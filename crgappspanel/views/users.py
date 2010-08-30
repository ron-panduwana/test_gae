import hashlib
import time
import urllib
from itertools import imap

from google.appengine.api import memcache
from google.appengine.api.labs import taskqueue
from django.core.urlresolvers import reverse
from django.shortcuts import redirect
from django.utils.translation import ugettext_lazy as _
from django.http import HttpResponseRedirect, Http404

import crauth
from crauth.decorators import login_required, admin_required, has_perm
from crauth.models import Role, UserPermissions
from crgappspanel import consts
from crgappspanel.forms import UserForm, UserRolesForm, UserGroupsForm, \
    UserEmailSettingsForm, UserEmailFiltersForm, UserEmailAliasesForm, \
    UserEmailVacationForm
from crgappspanel.helpers.misc import ValueWithRemoveLink
from crgappspanel.helpers.tables import Table, Column
from crgappspanel.helpers.paginator import Paginator
from crgappspanel.models import Preferences, GAUser, GANickname, GAGroup, \
        GAGroupOwner, GAGroupMember
from crgappspanel.views.utils import get_sortby_asc, get_page, qs_wo_page, \
        secure_random_chars, redirect_saved, render
from crlib.navigation import render_with_nav
from crlib import errors
from crgappspanel.navigation import user_nav


FORWARD_ACTIONS = dict(
    ek=consts.EMAIL_ACTION_KEEP,
    ea=consts.EMAIL_ACTION_ARCHIVE,
    ed=consts.EMAIL_ACTION_DELETE)
POP3_ENABLE_FORS = dict(
    ea=consts.EMAIL_ENABLE_FOR_ALL_MAIL,
    en=consts.EMAIL_ENABLE_FOR_MAIL_FROM_NOW_ON)


def _get_user_email(domain):
    def new(x):
        return '%s@%s' % (x.user_name or '', domain)
    return new

def _get_status(x):
    return _('Suspended') if x.suspended else _('Active')

def _get_quota(x):
    quota = x.quota
    if quota > 1024:
        return '%d GB' % (quota // 1024)
    else:
        return '%s MB' % quota

def _get_roles_map():
    """
    This method needs data access, make sure you don't call this method too many times to create
    performance issues.
    """
    roles_map=dict()
    for role in Role.for_domain(crauth.users.get_current_domain()).fetch(1000):
        roles_map[str(role.key())] = role
    return roles_map

def _get_role(key):
    key = str(key)
    roles_map = _get_roles_map()
    if key in roles_map:
        return roles_map[key]
    else:
        return None

def _get_roles(keys):
    return Role.get(keys)

def _get_roles_choices(role_keys, is_admin):
    choices = [('', '')]
    if not is_admin:
        choices.append(('admin', _('Administrator')))
    choices.extend([(k, v.name) for k, v in _get_roles_map().iteritems() if k not in role_keys])
    return choices

def _get_user_roles(domain):
    def new(x):
        if x.admin:
            return _('Administrator')
        
        from crauth.models import UserPermissions
        perms = UserPermissions.get_by_key_name(_get_user_email(domain)(x))
        if perms:
            return ', '.join(
                role.name for role in Role.get(perms.roles) if role)
        else:
            return ''
    return new

def _table_fields_gen(domain):
    return [
        Column(_('Name'), 'family_name', getter=lambda x: x.get_full_name(), link=True),
        Column(_('Username'), 'user_name', getter=_get_user_email(domain)),
        Column(_('Status'), 'suspended', getter=_get_status),
        Column(_('Roles'), 'admin', getter=_get_user_roles(domain),
               sortable=False),
        Column(_('Email quota'), 'quota', sortable=False),
    ]
_table_id = Column(None, 'user_name')
_table_widths = ['%d%%' % x for x in (5, 20, 30, 15, 20, 10)]


@has_perm('read_gauser')
def users(request):
    user = crauth.users.get_current_user()
    domain = user.domain_name
    _table_fields = _table_fields_gen(domain)
    
    per_page = Preferences.for_current_user().items_per_page
    paginator = Paginator(GAUser, request, (
        'user_name', 'family_name', 'suspended', 'admin',
    ), per_page)
    
    table = Table(_table_fields, _table_id)
    
    delete_link_title = _('Delete users')
    return render_with_nav(request, 'users_list.html', {
        'table': table.generate_paginator(
            paginator, widths=_table_widths,
            delete_link_title=delete_link_title,
            can_change=user.has_perm('change_gauser')),
        'saved': request.session.pop('saved', False),
        'delete_question': _('Are you sure you want to delete selected '
                             'users?'),
        'delete_link_title': delete_link_title,
    }, help_url='users/list')


@has_perm('add_gauser')
def user_create(request):
    domain = crauth.users.get_current_user().domain_name
    
    if request.method == 'POST':
        form = UserForm(request.POST, auto_id=True)
        if form.is_valid():
            user = form.create()
            try:
                user.save()
                return redirect_saved('user-details', request,
                                      name=user.user_name)
            except errors.EntityExistsError:
                form.add_error(
                    'user_name',
                    _('Either user or nick with this name already exists.'))
            except errors.EntityDeletedRecentlyError:
                form.add_error(
                    'user_name',
                    _('User with such name was recently deleted and this name '
                      'cannot be currently used.'))
            except errors.DomainUserLimitExceededError:
                form.add_error(
                    '__all__',
                    _('Your domain user limit has been reached, you cannot '
                      'create more users.'))
            except errors.UnknownGDataError:
                form.add_error(
                    'user_name',
                    _('Either user or nick with this name already exists.'))
            except errors.NetworkError:
                form.add_error(
                    '__all__',
                    _('An error occured during the request. Please try again.'))
    else:
        form = UserForm(auto_id=True)
        form.fields['user_name'].help_text = '@%s' % domain
    
    temp_password = secure_random_chars(8)
    
    return render_with_nav(request, 'user_create.html', {
        'form': form,
        'temp_password': temp_password,
        'exists': request.session.pop('exists', False),
    }, in_section='users/users', help_url='users/create')


@has_perm('change_gauser')
def user_details(request, name=None):
    if not name:
        raise ValueError('name = %s' % name)
    
    domain = crauth.users.get_current_user().domain_name
    user = GAUser.get_by_key_name(name)
    if not user:
        return redirect('users')
    
    if request.method == 'POST':
        form = UserForm(request.POST, auto_id=True)
        if form.is_valid():
            form.populate(user)
            try:
                user.save()
                try:
                    if form.get_nickname():
                        GANickname(
                            user=user,
                            nickname=form.get_nickname(),
                            user_name=user.user_name,
                        ).save()
                    return redirect_saved('user-details', request,
                                          name=user.user_name)
                except errors.EntityExistsError:
                    form.add_error(
                        'nicknames',
                        _('This name is already reserved.'))
            except errors.EntityExistsError:
                form.add_error(
                    'user_name',
                    _('Either user or nick with this name already exists.'))
            except errors.EntityDeletedRecentlyError:
                form.add_error(
                    'user_name',
                    _('User with such name was recently deleted and this name '
                      'cannot be currently used.'))
    else:
        form = UserForm(initial={
            'user_name': user.user_name,
            'password': '',
            'change_password': user.change_password,
            'full_name': [user.given_name, user.family_name],
            'admin': user.admin,
            'nicknames': '',
        }, auto_id=True)
        form.fields['user_name'].help_text = '@%s' % domain
    
    def get_email(x):
        return '%s@%s' % (x, domain)
    def remove_nick_link(x):
        kwargs = dict(name=user.user_name, nickname=x.nickname)
        return reverse('user-remove-nickname', kwargs=kwargs)
    full_nicknames = [ValueWithRemoveLink(get_email(nick.nickname),
            remove_nick_link(nick)) for nick in user.nicknames]
    return render_with_nav(request, 'user_details.html', {
        'user': user,
        'form': form,
        'full_nicknames': full_nicknames,
        'saved': request.session.pop('saved', False),
    }, extra_nav=user_nav(name), help_url='users/details')


@has_perm('read_role')
def user_roles(request, name=None):
    from crauth.models import AppsDomain, Role, UserPermissions
    auth = crauth.users.get_current_user()
    
    if not name:
        raise ValueError('name = %s' % name)
    
    user = GAUser.get_by_key_name(name)
    if not user:
        return redirect('users')
    
    email = '%s@%s' % (user.user_name, crauth.users.get_current_user().domain_name)
    perms = UserPermissions.get_or_insert(key_name=email, user_email=email)
    
    role_keys = [str(role_key) for role_key in perms.roles]
    
    if request.method == 'POST' and auth.has_perm('add_role'):
        form = UserRolesForm(request.POST, auto_id=True,
            choices=_get_roles_choices(role_keys, user.admin))
        if form.is_valid():
            data = form.cleaned_data
            
            roles = data['roles']
            if roles:
                if roles == 'admin':
                    user.admin = True
                    user.save()
                else:
                    perms.roles.append(_get_role(roles).key())
                    perms.save()
            return redirect_saved('user-roles', request, name=user.user_name)
    else:
        form = UserRolesForm(initial=dict(role=''), auto_id=True,
            choices=_get_roles_choices(role_keys, user.admin))
    
    def remove_role_link(x):
        kwargs = dict(name=user.user_name, role_name=x)
        return reverse('user-remove-role', kwargs=kwargs)
    roles = _get_roles(role_keys)
    roles_with_remove = [
        ValueWithRemoveLink(unicode(role.name).encode('UTF-8'),
                            remove_role_link(role.name))
        for role in roles if role]
    if user.admin:
        obj = ValueWithRemoveLink(_('Administrator'), remove_role_link('admin'))
        roles_with_remove.insert(0, obj)
    
    return render_with_nav(request, 'user_roles.html', {
        'user': user,
        'form': form,
        'roles': roles_with_remove,
        'saved': request.session.pop('saved', False),
    }, extra_nav=user_nav(name), help_url='users/roles')


@has_perm('change_gauser')
def user_groups(request, name=None):
    if not name:
        raise ValueError('name = %s' % name)

    wait_for = request.GET.get('wait_for')
    if wait_for:
        from google.appengine.runtime import DeadlineExceededError
        retry = int(request.GET.get('retry', 0))
        items_len = int(request.GET.get('len', 0))
        items_cur = memcache.get(wait_for)
        if items_cur is None:
            items_cur = items_len
        try:
            while items_cur < items_len:
                time.sleep(1)
                items_cur = memcache.get(wait_for)
        except DeadlineExceededError:
            if retry < 3:
                return HttpResponseRedirect(
                    request.path + '?' + urllib.urlencode({
                        'wait_for': wait_for,
                        'len': items_len,
                        'retry': retry + 1,
                    }))
        memcache.delete(wait_for)
    
    user = GAUser.get_by_key_name(name)
    if not user:
        return redirect('users')
    
    groups = GAGroup.all().order('name').fetch(1000)
    member_of = GAGroup.all().filter(
        'members', GAGroupMember.from_user(user)).fetch(1000)
    member_of_ids = [group.id for group in member_of]

    if request.method == 'POST':
        form = UserGroupsForm(request.POST, auto_id=True)
        form.fields['groups'].choices = [(group.id, group.name) for group in groups]
        
        if form.is_valid():
            data = form.cleaned_data
            
            as_owner = (data['add_as'] == 'owner')
            group_owner = GAGroupOwner.from_user(user)
            group_member = GAGroupMember.from_user(user)
            
            email = '%s@%s' % (user.user_name,
                               crauth.users.get_current_user().domain_name)
            hashed = hashlib.sha1(email + str(as_owner)).hexdigest()
            memcache.set(hashed, 0)
            for group_id in data['groups']:
                params = {
                    'email': email,
                    'group_id': group_id,
                    'as_owner': str(as_owner),
                    'hashed': hashed,
                }
                taskqueue.add(
                    url=reverse('add_user_to_group'),
                    params=params)
            return HttpResponseRedirect(
                request.path + '?wait_for=%s&len=%d' % (
                    hashed, len(data['groups'])))
    else:
        form = UserGroupsForm(auto_id=True)
        form.fields['groups'].choices = [
            (group.id, group.name) for group in groups
            if not group.id in member_of_ids]
    
    return render_with_nav(request, 'user_groups.html', {
        'user': user,
        'form': form,
        'member_of': member_of,
        'saved': request.session.pop('saved', False),
    }, extra_nav=user_nav(name), help_url='users/groups')


@has_perm('change_gausersettings')
def user_email_settings(request, name=None):
    if not name:
        raise ValueError('name = %s' % name)
    
    user = GAUser.get_by_key_name(name)
    if not user:
        return redirect('users')
    
    if request.method == 'POST':
        form = UserEmailSettingsForm(request.POST, auto_id=True)
        if form.is_valid():
            data = form.cleaned_data
            general = {}
            
            language = data['language']
            if language:
                ret = user.email_settings.update_language(language)
            
            forward = data['forward']
            forward_to = data['forward_to']
            forward_action = FORWARD_ACTIONS.get(forward)
            if forward_action is not None:
                user.email_settings.update_forwarding(True,
                    forward_to=forward_to, action=forward_action)
            elif forward == 'd':
                user.email_settings.update_forwarding(False)
            
            pop3 = data['pop3']
            pop3_enable_for = POP3_ENABLE_FORS.get(pop3)
            if pop3_enable_for is not None:
                user.email_settings.update_pop(True,
                    enable_for=pop3_enable_for, action=consts.EMAIL_ACTION_KEEP)
            elif pop3 == 'd':
                user.email_settings.update_pop(False)
            
            imap = form.get_boolean('imap')
            if imap is not None:
                user.email_settings.update_imap(imap)
            
            messages_per_page = data['messages_per_page']
            if messages_per_page in ('25', '50', '100'):
                general['page_size'] = int(messages_per_page)
            
            web_clips = form.get_boolean('web_clips')
            if web_clips is not None:
                user.email_settings.update_web_clip_settings(web_clips)
            
            general['snippets'] = form.get_boolean('snippets')
            general['shortcuts'] = form.get_boolean('shortcuts')
            general['arrows'] = form.get_boolean('arrows')
            general['unicode'] = form.get_boolean('unicode')
            general = dict((key, value) for key, value in general.iteritems() if value is not None)
            
            if len(general) > 0:
                user.email_settings.update_general(**general)
            
            signature = form.get_boolean('signature')
            signature_new = data['signature_new']
            if signature is not None:
                user.email_settings.update_signature(signature_new or '')
            
            return redirect_saved('user-email-settings',
                request, name=user.user_name)
    else:
        form = UserEmailSettingsForm(auto_id=True)
    
    return render_with_nav(request, 'user_email_settings.html', {
        'user': user,
        'form': form,
        'saved': request.session.pop('saved', False),
    }, extra_nav=user_nav(name), help_url='users/email-settings')


@has_perm('change_gauserfilters')
def user_email_filters(request, name=None):
    if not name:
        raise ValueError('name = %s' % name)
    
    user = GAUser.get_by_key_name(name)
    if not user:
        return redirect('users')
    
    if request.method == 'POST':
        form = UserEmailFiltersForm(request.POST, auto_id=True)
        if form.is_valid():
            data = dict((key, value) for key, value in form.cleaned_data.iteritems() if value)
            
            has_attachment = data.get('has_attachment')
            if has_attachment == 'e':
                data['has_attachment'] = True
            
            user.email_settings.create_filter(**data)
            return redirect_saved('user-email-filters',
                request, name=user.user_name)
    else:
        form = UserEmailFiltersForm(auto_id=True)
    
    return render_with_nav(request, 'user_email_filters.html', {
        'user': user,
        'form': form,
        'saved': request.session.pop('saved', False),
    }, extra_nav=user_nav(name), help_url='users/filters')


@has_perm('change_gauser')
def user_email_aliases(request, name=None):
    if not name:
        raise ValueError('name = %s' % name)
    
    user = GAUser.get_by_key_name(name)
    if not user:
        return redirect('users')
    
    if request.method == 'POST':
        form = UserEmailAliasesForm(request.POST, auto_id=True)
        if form.is_valid():
            data = dict((key, value) for key, value in form.cleaned_data.iteritems() if value)
            
            try:
                data['async'] = False
                user.email_settings.create_send_as_alias(**data)
                return redirect_saved('user-email-aliases',
                    request, name=user.user_name)
            except errors.EntityDoesNotExistError:
                form.add_error(
                    'address',
                    _('Email address has to exist as a user or an alias on '
                      '%s domain.' % crauth.users.get_current_domain().domain))
            except (errors.EntityNameNotValidError, errors.InvalidValueError):
                form.add_error(
                    'address',
                    _('Email address has to be of form username@%s' % (
                        crauth.users.get_current_domain().domain)))
    else:
        form = UserEmailAliasesForm(auto_id=True)
    
    return render_with_nav(request, 'user_email_aliases.html', {
        'user': user,
        'form': form,
        'saved': request.session.pop('saved', False),
    }, extra_nav=user_nav(name), help_url='users/aliases')


@has_perm('change_gauservacation')
def user_email_vacation(request, name):
    user = GAUser.get_by_key_name(name)
    if not user:
        raise Http404

    if request.method == 'POST':
        form = UserEmailVacationForm(request.POST)
        if form.is_valid():
            enabled = form.cleaned_data['state'] == 'true'
            if enabled:
                user.email_settings.update_vacation(
                    enabled,
                    subject=form.cleaned_data['subject'],
                    message=form.cleaned_data['message'],
                    contacts_only=form.cleaned_data['contacts_only'] == 'true')
            else:
                user.email_settings.update_vacation(enabled)
            return redirect_saved('user-email-vacation', request,
                                  name=user.user_name)
    else:
        form = UserEmailVacationForm()

    return render_with_nav(request, 'user_email_vacation.html', {
        'user': user,
        'form': form,
        'saved': request.session.pop('saved', False),
    }, extra_nav=user_nav(name), help_url='users/vacation')


@has_perm('change_gauser')
def user_suspend_restore(request, name=None, suspend=None):
    if not name or suspend is None:
        raise ValueError('name = %s, suspend = %s' % (name, str(suspend)))
    
    user = GAUser.get_by_key_name(name)
    user.suspended = suspend
    user.save()
    
    return redirect('user-details', name=user.user_name)


@has_perm('change_gauser')
def user_suspend(request, name=None):
    return user_suspend_restore(request, name=name, suspend=True)


@has_perm('change_gauser')
def user_restore(request, name=None):
    return user_suspend_restore(request, name=name, suspend=False)


@has_perm('change_gauser')
def user_remove(request, names=None):
    if not names:
        raise ValueError('names = %s' % names)
    
    for name in names.split('/'):
        user = GAUser.get_by_key_name(name)
        user.delete()
    
    return redirect_saved('users', request)


@has_perm('change_gauser')
def user_remove_nickname(request, name=None, nickname=None):
    if not all((name, nickname)):
        raise ValueError('name = %s, nickname = %s' % (name, nickname))
    
    nickname = GANickname.get_by_key_name(nickname)
    nickname.delete()
    
    return redirect_saved('user-details', request, name=name)


@has_perm('change_role')
def user_remove_role(request, name=None, role_name=None):
    if not all((name, role_name)):
        raise ValueError('name = %s, role_name = %s' % (name, role_name))
    
    if not name:
        raise ValueError('name = %s' % name)
    
    user = GAUser.get_by_key_name(name)
    if not user:
        return redirect('users')
    
    email = '%s@%s' % (user.user_name, crauth.users.get_current_user().domain_name)
    perms = UserPermissions.get_or_insert(key_name=email, user_email=email)
    
    if role_name == 'admin':
        user.admin = False
        user.save()
    else:
        roles = _get_roles([str(key) for key in perms.roles])
        perms.roles = [role.key() for role in roles if role.name != role_name]
        perms.save()
    
    return redirect_saved('user-roles', request, name=user.user_name)
