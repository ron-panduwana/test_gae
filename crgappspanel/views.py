from __future__ import with_statement
from google.appengine.api import memcache
from django import forms
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response, redirect

from crgappspanel.forms import UserForm
from crgappspanel.models import GAUser, GANickname
from crgappspanel.tables import Table, Column

# sample data - to be removed in some future
from crgappspanel.sample_data import get_sample_users, get_sample_groups

# temporary domain extraction
with open('google_apps.txt') as f:
    f.readline()
    f.readline()
    _domain = f.readline().strip()

def _get_status(x):
    suspended, admin = getattr(x, 'suspended'), getattr(x, 'admin')
    return 'Suspended' if suspended else 'Administrator' if admin else ''

_userFields = [
    Column('Name', 'name', getter=lambda x: x.get_full_name()),
    Column('Username', 'username', getter=lambda x: '%s@%s' % (getattr(x, 'user_name', ''), _domain)),
    Column('Status', 'status', getter=_get_status),
    Column('Email quota', 'quota', getter=lambda x: getattr(x, 'quota', '')),
    Column('Roles', 'roles', getter=lambda x: getattr(x, 'roles', '')),
    Column('Last signed in', 'last_login', getter=lambda x: getattr(x, 'last_login', ''))
]
_userId = Column('Username', 'user_name')

_groupFields = [
    Column('Name', 'title'),
    Column('Email address', 'name'),
    Column('Type', 'kind'),
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
    return render_to_response('index.html', dict(pages=['users', 'groups', 'test']))

def users(request):
    sortby, asc = _get_sortby_asc(request, [f.name for f in _userFields])
    
    users = GAUser.all().fetch(100)
    
    table = Table(_userFields, _userId, sortby=sortby, asc=asc)
    table.sort(users)
    
    return render_to_response('users_list.html', {'table': table.generate(users, widths=_userWidths), 'domain': _domain})

def user(request, name=None):
    if not name:
        raise ValueError('name = %s' % name)
        return redirect('crgappspanel.views.users')
    
    user = GAUser.get_by_key_name(name)
    
    if request.method == 'POST':
        form = UserForm(request.POST, auto_id=True)
        if form.is_valid():
            user.given_name = form['given_name']
            return redirect('crgappspanel.views.user', name=name)
    else:
        form = UserForm(initial={
            'user_name': '%s@%s' % (user.user_name, _domain),
            'given_name': user.given_name,
            'family_name': user.family_name,
            'admin': user.admin,
        }, auto_id=True)
    
    return render_to_response('user_details.html', {
        'domain': _domain,
        'name': name,
        'given_name': user.given_name,
        'family_name': user.family_name,
        'form': form,
    })

def user_action(request, name=None, action=None):
    if not all(name, action):
        raise ValueError('name = %s, action = %s' % (name, action))
        return redirect('crgappspanel.views.users')
    
    user = GAUser.get_by_key_name(name)
    
    # TODO ...

def groups(request):
    sortby, asc = _get_sortby_asc(request, [f.name for f in _groupFields])
    
    groups = get_sample_groups()
    table = Table(_groupFields, _groupId, sortby=sortby, asc=asc)
    table.sort(groups)
    
    return render_to_response('groups_list.html', {'table': table.generate(groups, widths=_groupWidths), 'domain': _domain})

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


def captcha(request, captcha_hash):
    redirect_to = request.GET.get('redirect_to', '/')
    if request.method == 'POST':
        email = request.POST.get('email', '')
        if email:
            memcache.set('captcha_response:%s' % email, request.POST, 5 * 60)
    else:
        captcha_info = memcache.get('captcha:%s' % captcha_hash)
        if captcha_info is not None:
            return render_to_response('captcha.html', captcha_info)
    return HttpResponseRedirect(redirect_to)

