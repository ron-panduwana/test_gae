from __future__ import with_statement

import os

from django import forms
from django.http import HttpResponse
from django.shortcuts import render_to_response, redirect
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext as _

from crgappspanel.consts import EMAIL_RELS
from crgappspanel.forms import UserForm, SharedContactForm
from crgappspanel.models import GAUser, GANickname, SharedContact, Email
from crgappspanel.helpers.filters import NullFilter, AnyAttributeFilter, AllAttributeFilter
from crgappspanel.helpers.tables import Table, Column
from crlib.users import admin_required
from settings import APPS_DOMAIN, LANGUAGES

# sample data - to be removed in some future
from crgappspanel.sample_data import get_sample_users, get_sample_groups


def _get_status(x):
    suspended, admin = getattr(x, 'suspended'), getattr(x, 'admin')
    return _('Suspended') if x.suspended else _('Administrator') if x.admin else ''

def _get_sortby_asc(request, valid):
    sortby = request.GET.get('sortby', None)
    asc = (request.GET.get('asc', 'true') == 'true')
    if not sortby in valid:
        sortby = None
    return (sortby, asc)

_password_chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
def _get_password_char(n1, n2):
    return _password_chars[(256 * n1 + n2) % len(_password_chars)]

def _random_password(chars):
    bts = os.urandom(2 * chars)
    return ''.join(_get_password_char(ord(b1), ord(b2)) for b1, b2 in zip(bts[:chars], bts[chars:]))


def ctx(d, section=None, subsection=None, back=False):
    from crgappspanel.sections import SECTIONS
    d['domain'] = APPS_DOMAIN
    d['sections'] = SECTIONS
    if section is not None:
        d['sel_section'] = SECTIONS[section - 1]
        if subsection is not None:
            d['sel_subsection'] = SECTIONS[section - 1]['subsections'][subsection - 1]
        d['back_button'] = back
    return d


def index(request):
    return redirect('users')


################################################################################
#                                    GROUPS                                    #
################################################################################


_groupFields = [
    Column(_('Name'), 'title', link=True),
    Column(_('Email address'), 'name'),
    Column(_('Type'), 'kind'),
]
_groupId = _groupFields[1]
_groupWidths = ['%d%%' % x for x in (5, 40, 40, 15)]


@admin_required
def groups(request):
    sortby, asc = _get_sortby_asc(request, [f.name for f in _groupFields])
    
    groups = get_sample_groups()
    table = Table(_groupFields, _groupId, sortby=sortby, asc=asc)
    table.sort(groups)
    
    return render_to_response('groups_list.html', ctx({
        'table': table.generate(groups, widths=_groupWidths, singular='group'),
        'styles': ['table-list'],
        'scripts': ['table'],
    }, 2, 1))


################################################################################
#                                    USERS                                     #
################################################################################


_userFields = [
    Column(_('Name'), 'name', getter=lambda x: x.get_full_name(), link=True),
    Column(_('Username'), 'username', getter=lambda x: '%s@%s' % (x.user_name or '', APPS_DOMAIN)),
    Column(_('Status'), 'status', getter=_get_status),
    Column(_('Email quota'), 'quota'),
    Column(_('Roles'), 'roles', getter=lambda x: ''),
    Column(_('Last signed in'), 'last_login', getter=lambda x: '')
]
_userId = Column(None, 'user_name')
_userWidths = ['%d%%' % x for x in (5, 15, 25, 15, 15, 15, 10)]


@admin_required
def users(request):
    sortby, asc = _get_sortby_asc(request, [f.name for f in _userFields])
    
    users = GAUser.all().fetch(100)
    
    table = Table(_userFields, _userId, sortby=sortby, asc=asc)
    table.sort(users)
    
    return render_to_response('users_list.html', ctx({
        'table': table.generate(users, widths=_userWidths, singular='user'),
        'styles': ['table-list'],
        'scripts': ['table'],
    }, 2, 2))


@admin_required
def user_create(request):
    if request.method == 'POST':
        form = UserForm(request.POST, auto_id=True)
        if form.is_valid():
            user = form.create()
            user.save()
            return redirect('user-details', name=user.user_name)
    else:
        form = UserForm(auto_id=True)
        form.fields['user_name'].help_text = '@%s' % APPS_DOMAIN
    
    temp_password = _random_password(6)
    
    return render_to_response('user_create.html', ctx({
        'form': form,
        'temp_password': temp_password,
    }, 2, 2, True))


@admin_required
def user_details(request, name=None):
    if not name:
        raise ValueError('name = %s' % name)
    
    user = GAUser.get_by_key_name(name)
    if not user:
        return redirect('users')
    
    if request.method == 'POST':
        form = UserForm(request.POST, auto_id=True)
        if form.is_valid():
            form.populate(user)
            user.save()
            if form.get_nickname():
                GANickname(user=user, nickname=form.get_nickname()).save()
            return redirect('user-details', name=user.user_name)
    else:
        form = UserForm(initial={
            'user_name': user.user_name,
            'password': '',
            'change_password': user.change_password,
            'full_name': [user.given_name, user.family_name],
            'admin': user.admin,
            'nicknames': '',
        }, auto_id=True)
        form.fields['user_name'].help_text = '@%s' % APPS_DOMAIN
    
    fmt = '<b>%s</b>@%s - <a href="%s">Remove</a>'
    def remove_nick_link(x):
        kwargs = dict(name=user.user_name, nickname=x.nickname)
        return reverse('user-remove-nickname', kwargs=kwargs)
    full_nicknames = [fmt % (nick.nickname, APPS_DOMAIN, remove_nick_link(nick)) for nick in user.nicknames]
    return render_to_response('user_details.html', ctx({
        'user': user,
        'form': form,
        'full_nicknames': full_nicknames,
        'styles': ['table-details', 'user-details'],
        'scripts': ['expand-field', 'swap-widget', 'user-details'],
    }, 2, 2, True))


def user_suspend_restore(request, name=None, suspend=None):
    if not name or suspend is None:
        raise ValueError('name = %s, suspend = %s' % (name, str(suspend)))
    
    user = GAUser.get_by_key_name(name)
    user.suspended = suspend
    user.save()
    
    return redirect('user-details', name=user.user_name)


@admin_required
def user_suspend(request, name=None):
    return user_suspend_restore(request, name=name, suspend=True)


@admin_required
def user_restore(request, name=None):
    return user_suspend_restore(request, name=name, suspend=False)


@admin_required
def user_remove(request, names=None):
    if not names:
        raise ValueError('names = %s' % names)
    
    for name in names.split('/'):
        user = GAUser.get_by_key_name(name)
        user.delete()
    
    return redirect('users')


@admin_required
def user_remove_nickname(request, name=None, nickname=None):
    if not all((name, nickname)):
        raise ValueError('name = %s, nickname = %s' % (name, nickname))
    
    nickname = GANickname.get_by_key_name(nickname)
    nickname.delete()
    
    return redirect('user-details', name=name)


################################################################################
#                               SHARED CONTACTS                                #
################################################################################


_sharedContactFields = [
    Column(_('Name'), 'full_name', getter=lambda x: x.name.full_name, link=True),
    Column(_('Given name'), 'given_name', getter=lambda x: x.name.given_name),
    Column(_('Family name'), 'family_name', getter=lambda x: x.name.family_name),
    Column(_('E-mails'), 'emails', getter=lambda x: '\n'.join(y.address for y in x.emails)),
]
_sharedContactId = _sharedContactFields[0]
_sharedContactWidths = ['%d%%' % x for x in (5, 20, 20, 20, 35)]


@admin_required
def shared_contacts(request):
    sortby, asc = _get_sortby_asc(request, [f.name for f in _sharedContactFields])
    
    query = request.GET.get('q', '')
    query_name = request.GET.get('name', '')
    query_notes = request.GET.get('notes', '')
    query_email = request.GET.get('email', '')
    
    shared_contacts = SharedContact.all().fetch(100)
    
    if query:
        advanced_search = False
        filter = AnyAttributeFilter({
            'name.full_name': query,
            'name.given_name': query,
            'name.family_name': query,
            'notes': query,
            'emails.address': query,
        })
        filters = ['%s:%s' % (_('query'), query)]
    elif any((query_name, query_notes, query_email)):
        advanced_search = True
        filters = []
        filter_args = dict()
        if query_name:
            filters.append('%s:%s' % (_('name'), query_name))
            filter_args['name.full_name'] = query_name
        if query_notes:
            filters.append('%s:%s' % (_('notes'), query_notes))
            filter_args['notes'] = query_notes
        if query_email:
            filters.append('%s:%s' % (_('email'), query_email))
            filter_args['emails.address'] = query_email
        filter = AllAttributeFilter(filter_args)
    else:
        advanced_search = False
        filter = NullFilter()
        filters = None
    
    shared_contacts = [x for x in shared_contacts if filter.match(x)]
    
    table = Table(_sharedContactFields, _sharedContactId, sortby=sortby, asc=asc)
    table.sort(shared_contacts)
    
    return render_to_response('shared_contacts_list.html', ctx({
        'table': table.generate(shared_contacts, widths=_sharedContactWidths, singular='shared contact'),
        'advanced_search': advanced_search,
        'filters': filters,
        'query': dict(general=query, name=query_name, notes=query_notes, email=query_email),
        'styles': ['table-list'],
        'scripts': ['table', 'shared-contacts-list'],
    }, 3))


@admin_required
def shared_contact_add(request):
    if request.method == 'POST':
        form = SharedContactForm(request.POST, auto_id=True)
        if form.is_valid():
            shared_contact = form.create()
            shared_contact.name.save()
            for email in shared_contact.emails:
                email.save()
            shared_contact.save()
            return redirect('shared-contact-details', name=shared_contact.name)
    else:
        form = SharedContactForm(auto_id=True)
    
    return render_to_response('shared_contact_add.html', ctx({
        'form': form,
        'styles': ['table-details'],
    }, 3, None, True))


@admin_required
def shared_contact_details(request, name=None):
    if not name:
        raise ValueError('name = %s' % name)
    
    shared_contact = SharedContact.get_by_key_name(name)
    if not shared_contact:
        return redirect('shared-contacts')
    
    if request.method == 'POST':
        form = SharedContactForm(request.POST, auto_id=True)
        if form.is_valid():
            new_objects = form.populate(shared_contact)
            shared_contact.name.save()
            
            for email in new_objects['emails']:
                email.save()
                shared_contact.emails.append(email)
            
            for phone_number in new_objects['phone_numbers']:
                phone_number.save()
                shared_contact.phone_numbers.append(phone_number)
            
            company_str = new_objects.get('company_str', None)
            if company_str:
                company = shared_contact.set_extended_property('company', company_str)
                company.save()
            
            role_str = new_objects.get('role_str', None)
            if role_str:
                role = shared_contact.set_extended_property('role', role_str)
                role.save()
            
            shared_contact.save()
            return redirect('shared-contact-details', name=shared_contact.name.full_name)
    else:
        real_name = [shared_contact.name.name_prefix,
                shared_contact.name.given_name, shared_contact.name.family_name]
        form = SharedContactForm(initial={
            'full_name': shared_contact.name.full_name,
            'real_name': real_name,
            'company': shared_contact.get_extended_property('company', ''),
            'role': shared_contact.get_extended_property('role', ''),
            'notes': shared_contact.notes,
            'emails': '',
        }, auto_id=True)
    
    fmt = '<b>%s</b>@%s - <a href="%s">Remove</a>'
    def remove_email_link(x):
        kwargs=dict(name=shared_contact.name, action='remove-email', arg=x.address)
        return reverse('shared-contact-action', kwargs=kwargs)
    return render_to_response('shared_contact_details.html', ctx({
        'shared_contact': shared_contact,
        'form': form,
        'all_emails': (email.address for email in shared_contact.emails),
        'all_phone_numbers': (phone.number for phone in shared_contact.phone_numbers),
        'styles': ['table-details'],
        'scripts': ['swap-widget'],
    }, 3, None, True))


@admin_required
def shared_contact_remove(request, names=None):
    if not names:
        raise ValueError('names = %s' % names)
    
    for name in names.split('/'):
        user = SharedContact.get_by_key_name(name)
        user.delete()
    
    return redirect('shared-contacts')


################################################################################
#                                    OTHERS                                    #
################################################################################


def language(request):
    return render_to_response('language.html', {'LANGUAGES': LANGUAGES})


@admin_required
def test(request):
    return render_to_response('test.html', ctx({
        'scripts': ['test'],
    }, 2, 4))
