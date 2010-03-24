from __future__ import with_statement
import logging
from google.appengine.api import memcache
from django import forms
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response, redirect
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext as _

from crgappspanel.forms import UserForm, LoginForm
from crgappspanel.models import GAUser, GANickname
from crgappspanel.helpers.tables import Table, Column
from crgappspanel.decorators import admin_required, CLIENT_LOGIN_INFO, \
        CLIENT_LOGIN_TOKEN_KEY
from settings import APPS_DOMAIN, LANGUAGES

# sample data - to be removed in some future
from crgappspanel.sample_data import get_sample_users, get_sample_groups

def _get_status(x):
    suspended, admin = getattr(x, 'suspended'), getattr(x, 'admin')
    return _('Suspended') if x.suspended else _('Administrator') if x.admin else ''

_userFields = [
    Column(_('Name'), 'name', getter=lambda x: x.get_full_name()),
    Column(_('Username'), 'username', getter=lambda x: '%s@%s' % (getattr(x, 'user_name', ''), APPS_DOMAIN)),
    Column(_('Status'), 'status', getter=_get_status),
    Column(_('Email quota'), 'quota', getter=lambda x: getattr(x, 'quota', '')),
    Column(_('Roles'), 'roles', getter=lambda x: getattr(x, 'roles', '')),
    Column(_('Last signed in'), 'last_login', getter=lambda x: getattr(x, 'last_login', ''))
]
_userId = Column(None, 'user_name')

_groupFields = [
    Column(_('Name'), 'title'),
    Column(_('Email address'), 'name'),
    Column(_('Type'), 'kind'),
]
_groupId = _groupFields[1]

_userWidths = ['%d%%' % x for x in (5, 15, 25, 15, 15, 15, 10)]
_groupWidths = ['%d%%' % x for x in (5, 40, 40, 15)]

def _get_sortby_asc(request, valid):
    sortby = request.GET.get('sortby', None)
    asc = (request.GET.get('asc', 'true') == 'true')
    if not sortby in valid:
        sortby = None
    return (sortby, asc)

def index(request):
    return render_to_response('index.html', dict(pages=['users', 'groups', 'language', 'test']))

@admin_required
def users(request):
    sortby, asc = _get_sortby_asc(request, [f.name for f in _userFields])
    
    users = GAUser.all().fetch(100)
    
    table = Table(_userFields, _userId, sortby=sortby, asc=asc)
    table.sort(users)
    
    return render_to_response('users_list.html', {
        'table': table.generate(users, widths=_userWidths),
        'domain': APPS_DOMAIN})

@admin_required
def user(request, name=None):
    if not name:
        raise ValueError('name = %s' % name)
    
    user = GAUser.get_by_key_name(name)
    if not user:
        return redirect('crgappspanel.views.users')
    
    if request.method == 'POST':
        form = UserForm(request.POST, auto_id=True)
        if form.is_valid():
            form.set_data(user)
            user.save()
            return redirect('crgappspanel.views.user', name=user.user_name)
    else:
        form = UserForm(initial={
            'user_name': user.user_name,
            'given_name': user.given_name,
            'family_name': user.family_name,
            'admin': user.admin,
        }, auto_id=True)
        form.fields['user_name'].help_text = '@%s' % APPS_DOMAIN
    
    return render_to_response('user_details.html', {
        'domain': APPS_DOMAIN,
        'user': user,
        'form': form,
    })

@admin_required
def user_action(request, name=None, action=None):
    if not all((name, action)):
        raise ValueError('name = %s, action = %s' % (name, action))
    
    user = GAUser.get_by_key_name(name)
    
    if action == 'suspend':
        user.suspended = True
        user.save()
    elif action == '!suspend':
        user.suspended = False
        user.save()
    else:
        raise ValueError('unknown action: %s' % action)
    return redirect('crgappspanel.views.user', name=user.user_name)

@admin_required
def groups(request):
    sortby, asc = _get_sortby_asc(request, [f.name for f in _groupFields])
    
    groups = get_sample_groups()
    table = Table(_groupFields, _groupId, sortby=sortby, asc=asc)
    table.sort(groups)
    
    return render_to_response('groups_list.html', {
        'table': table.generate(groups, widths=_groupWidths),
        'domain': APPS_DOMAIN})


def logout(request):
    try:
        request.session.flush()
    except TypeError:
        pass
    return HttpResponseRedirect('/')


def login(request):
    redirect_to = request.GET.get(
        'redirect_to', request.META.get('HTTP_REFERER', '/'))
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            email = '%s@%s' % (form.cleaned_data['user_name'], APPS_DOMAIN)
            request.session[CLIENT_LOGIN_INFO] = {
                'domain': APPS_DOMAIN,
                'email': email,
                'password': form.cleaned_data['password'],
            }
            memcache.set(
                CLIENT_LOGIN_TOKEN_KEY % email, form.token, 24 * 60 * 60)
            return HttpResponseRedirect(redirect_to)
    else:
        form = LoginForm()
    ctx = {
        'form': form,
        'domain': APPS_DOMAIN,
    }
    return render_to_response('login.html', ctx)

def language(request):
    return render_to_response('language.html', {'LANGUAGES': LANGUAGES})

@admin_required
def test(request):
    users = GAUser.all().fetch(100)
    
    res = ''
    for index, user in enumerate(users):
        res += 'users[%d]:\n' % index
        for field_name in ['given_name', 'family_name', 'user_name', 'password', 'suspended', 'admin']:
            field_value = getattr(user, field_name)
            res += '  %s: %s [%s]\n' % (field_name, field_value, str(type(field_value)))
        res += '\n'
    res += '\n'
    
    nicknames = GANickname.all().fetch(100)
    for index, nickname in enumerate(nicknames):
        res += 'nicknames[%d]: %s\n' % (index, nickname.nickname)
    res += '\n'
    
    return HttpResponse(res, mimetype='text/plain')
