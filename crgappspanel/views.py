from __future__ import with_statement

import os

from django import forms
from django.http import HttpResponse
from django.shortcuts import render_to_response, redirect
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext as _

from crgappspanel.forms import UserForm
from crgappspanel.models import GAUser, GANickname, SharedContact
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
#                                    USERS                                     #
################################################################################


_userFields = [
    Column(_('Name'), 'name', getter=lambda x: x.get_full_name()),
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
        'scripts': ['table', 'users-list'],
    }, 2, 1))


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
    }, 2, 1, True))


@admin_required
def user(request, name=None):
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
        kwargs=dict(name=user.user_name, action='remove-nickname', arg=str(x))
        return reverse('user-action', kwargs=kwargs)
    full_nicknames = [fmt % (nick, APPS_DOMAIN, remove_nick_link(nick)) for nick in user.nicknames]
    return render_to_response('user_details.html', ctx({
        'user': user,
        'form': form,
        'full_nicknames': full_nicknames,
        'styles': ['table-details', 'user-details'],
        'scripts': ['expand-field', 'swap-widget', 'user-details'],
    }, 2, 1, True))


@admin_required
def user_action(request, name=None, action=None, arg=None):
    if not all((name, action)):
        raise ValueError('name = %s, action = %s' % (name, action))
    
    user = GAUser.get_by_key_name(name)
    
    if action == 'suspend':
        user.suspended = True
        user.save()
    elif action == '!suspend':
        user.suspended = False
        user.save()
    elif action == 'remove':
        user.delete()
        return redirect('users')
    elif action == 'remove-nickname':
        if not arg:
            raise ValueError('arg = %s' % arg)
        nickname = GANickname.get_by_key_name(arg)
        nickname.delete()
    else:
        raise ValueError('Unknown action: %s' % action)
    return redirect('user-details', name=user.user_name)


################################################################################
#                                    GROUPS                                    #
################################################################################


_groupFields = [
    Column(_('Name'), 'title'),
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
    }, 2, 2))


################################################################################
#                               SHARED CONTACTS                                #
################################################################################


_sharedContactFields = [
    Column(_('Name'), 'title'),
    Column(_('Notes'), 'notes', default=''),
    Column(_('E-mails'), 'emails', getter=lambda x: '\n'.join(y.address for y in x.emails)),
]
_sharedContactId = _sharedContactFields[0]
_sharedContactWidths = ['%d%%' % x for x in (5, 25, 25, 45)]


@admin_required
def shared_contacts(request):
    sortby, asc = _get_sortby_asc(request, [f.name for f in _sharedContactFields])
    
    sharedContacts = SharedContact.all().fetch(100)
    
    table = Table(_sharedContactFields, _sharedContactId, sortby=sortby, asc=asc)
    table.sort(sharedContacts)
    
    return render_to_response('shared_contacts_list.html', ctx({
        'table': table.generate(sharedContacts, widths=_sharedContactWidths, singular='shared contact'),
        'styles': ['table-list'],
        'scripts': ['table', 'shared-contacts-list'],
    }, 2, 5))


def shared_contact_add(request):
    pass


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
