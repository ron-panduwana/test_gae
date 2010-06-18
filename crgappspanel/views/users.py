from itertools import imap

from django.core.urlresolvers import reverse
from django.shortcuts import redirect
from django.utils.translation import ugettext as _

import crauth
from crauth.decorators import login_required, admin_required, has_perm
from crauth.models import Role, UserPermissions
from crgappspanel import consts
from crgappspanel.forms import UserForm, UserRolesForm, UserGroupsForm, \
    UserEmailSettingsForm, UserEmailFiltersForm, UserEmailAliasesForm
from crgappspanel.helpers.misc import ValueWithRemoveLink
from crgappspanel.helpers.tables import Table, Column
from crgappspanel.models import GAUser, GANickname, GAGroup, GAGroupOwner, GAGroupMember
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

def _cached_roles(roles_map=dict()):
    if len(roles_map) == 0:
        for role in Role.for_domain(crauth.users.get_current_domain()).fetch(1000):
            roles_map[str(role.key())] = role
    return roles_map

def _get_role(key):
    key = str(key)
    if key in _cached_roles():
        return _cached_roles()[key]
    else:
        return None

def _get_roles(keys):
    res = imap(lambda x: _get_role(x), keys)
    return [x for x in res if x is not None]

def _get_roles_choices(role_keys, is_admin):
    choices = [('', '')]
    if not is_admin:
        choices.append(('admin', _('Administrator')))
    
    new_role_keys = [key for key in _cached_roles().iterkeys() if key not in role_keys]
    choices.extend([(key, _get_role(key).name) for key in new_role_keys])
    return choices

def _get_user_roles(domain):
    def new(x):
        if x.admin:
            return _('Administrator')
        
        from crauth.models import UserPermissions
        perms = UserPermissions.get_by_key_name(_get_user_email(domain)(x))
        if perms:
            return ', '.join(role.name for role in _get_roles(perms.roles))
        else:
            return ''
    return new

def _table_fields_gen(domain):
    return [
        Column(_('Name'), 'name', getter=lambda x: x.get_full_name(), link=True),
        Column(_('Username'), 'username', getter=_get_user_email(domain)),
        Column(_('Status'), 'status', getter=_get_status),
        Column(_('Roles'), 'roles', getter=_get_user_roles(domain)),
        Column(_('Email quota'), 'quota'),
    ]
_table_id = Column(None, 'user_name')
_table_widths = ['%d%%' % x for x in (5, 20, 30, 15, 20, 10)]


@has_perm('read_gauser')
def users(request):
    user = crauth.users.get_current_user()
    domain = user.domain_name
    _table_fields = _table_fields_gen(domain)
    sortby, asc = get_sortby_asc(request, [f.name for f in _table_fields])
    
    users = GAUser.all().fetch(1000)
    
    # instantiating table and sorting users
    table = Table(_table_fields, _table_id, sortby=sortby, asc=asc)
    table.sort(users)
    
    # selecting particular page
    page = get_page(request, users, 20)
    
    return render_with_nav(request, 'users_list.html', {
        'table': table.generate(
            page.object_list, page=page, qs_wo_page=qs_wo_page(request),
            widths=_table_widths, singular='user',
            can_change=user.has_perm('change_gauser')),
        'saved': request.session.pop('saved', False),
    })


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
    else:
        form = UserForm(auto_id=True)
        form.fields['user_name'].help_text = '@%s' % domain
    
    temp_password = secure_random_chars(8)
    
    return render_with_nav(request, 'user_create.html', {
        'form': form,
        'temp_password': temp_password,
        'exists': request.session.pop('exists', False),
    }, in_section='users/users')


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
                            user=user,nickname=form.get_nickname()).save()
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
    }, extra_nav=user_nav(name))


@admin_required
def user_roles(request, name=None):
    from crauth.models import AppsDomain, Role, UserPermissions
    
    if not name:
        raise ValueError('name = %s' % name)
    
    user = GAUser.get_by_key_name(name)
    if not user:
        return redirect('users')
    
    email = '%s@%s' % (user.user_name, crauth.users.get_current_user().domain_name)
    perms = UserPermissions.get_or_insert(key_name=email, user_email=email)
    
    role_keys = [str(role_key) for role_key in perms.roles]
    
    if request.method == 'POST':
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
    roles_with_remove = [ValueWithRemoveLink(role.name, remove_role_link(role.name))
        for role in roles]
    if user.admin:
        obj = ValueWithRemoveLink(_('Administrator'), remove_role_link('admin'))
        roles_with_remove.insert(0, obj)
    
    return render_with_nav(request, 'user_roles.html', {
        'user': user,
        'form': form,
        'roles': roles_with_remove,
        'saved': request.session.pop('saved', False),
    }, extra_nav=user_nav(name))


@has_perm('change_gauser')
def user_groups(request, name=None):
    if not name:
        raise ValueError('name = %s' % name)
    
    user = GAUser.get_by_key_name(name)
    if not user:
        return redirect('users')
    
    groups = GAGroup.all().fetch(1000)
    if request.method == 'POST':
        form = UserGroupsForm(request.POST, auto_id=True)
        form.fields['groups'].choices = [(group.id, group.name) for group in groups]
        
        if form.is_valid():
            data = form.cleaned_data
            
            as_owner = (data['add_as'] == 'owner')
            group_owner = GAGroupOwner.from_user(user)
            group_member = GAGroupMember.from_user(user)
            
            for group_id in data['groups']:
                group = [group for group in groups if group.id == group_id]
                if group and user not in group[0].members:
                    if as_owner:
                        group[0].owners.append(group_owner)
                    group[0].members.append(group_member)
                    group[0].save()
            
            return redirect_saved('user-groups',
                request, name=user.user_name)
    else:
        form = UserGroupsForm(auto_id=True)
        form.fields['groups'].choices = [(group.id, group.name) for group in groups]
    
    member_of = GAGroup.all().filter('members', GAGroupMember.from_user(user)).fetch(1000)
    
    return render_with_nav(request, 'user_groups.html', {
        'user': user,
        'form': form,
        'member_of': [group.id for group in member_of],
        'saved': request.session.pop('saved', False),
    }, extra_nav=user_nav(name))


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
    }, extra_nav=user_nav(name))


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
    }, extra_nav=user_nav(name))


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
            
            user.email_settings.create_send_as_alias(**data)
            return redirect_saved('user-email-aliases',
                request, name=user.user_name)
    else:
        form = UserEmailAliasesForm(auto_id=True)
    
    return render_with_nav(request, 'user_email_aliases.html', {
        'user': user,
        'form': form,
        'saved': request.session.pop('saved', False),
    }, extra_nav=user_nav(name))


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


@admin_required
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
        perms.roles = [rk for rk in perms.roles if _get_role(rk).name != role_name]
        perms.save()
    
    return redirect_saved('user-roles', request, name=user.user_name)
