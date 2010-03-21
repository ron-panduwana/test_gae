from django import forms
from django.http import HttpResponse
from django.shortcuts import render_to_response, redirect
from crgappspanel.tables import Table, Column
from crgappspanel.models import GAUser

_users = [
    {
        'given_name': 'Pawel',
        'family_name': 'Zaborski',
        'user_name': 'pawel@moroccanholidayrental.com',
        'admin': 'True',
        'quota': '0% of 25 GB',
        'roles': 'admin',
        'last_login': '9:28 pm',
    },
    {
        'given_name': 'Roland',
        'family_name': 'Plaszowski',
        'user_name': 'roland@moroccanholidayrental.com',
        'admin': 'True',
        'quota': '0% of 25 GB',
        'roles': 'admin',
        'last_login': 'Jan 6',
    },
    {
        'given_name': 'Kamil',
        'family_name': 'Klimkiewicz',
        'user_name': 'kamil@moroccanholidayrental.com',
        'admin': 'True',
        'quota': '0% of 25 GB',
        'roles': 'admin',
        'last_login': '3:15 pm',
    },
    {
        'given_name': 'sky',
        'family_name': 'mail',
        'user_name': 'skymail@moroccanholidayrental.com',
        'admin': 'False',
        'quota': '3% of 25 GB',
        'roles': 'sample',
        'last_login': 'Mar 15',
    },
]

_groups = [
    {
        'name': 'Agent Portugal',
        'email': 'agent.pt@moroccanholidayrental.com',
        'type': 'Custom',
    },
    {
        'name': 'All Polish speakers',
        'email': 'all.polish.speakers@moroccanholidayrental.com',
        'type': 'Custom',
    },
]

def _get_name(x):
    try:
        given_name, family_name = x['given_name'], x['family_name']
    except:
        given_name, family_name = x.given_name, x.family_name
    
    return '%s %s' % (given_name, family_name)

def _get_status(x):
    try:
        suspended = x['suspended']
        admin = x['admin']
    except:
        suspended = x.suspended
        admin = x.admin
    
    if suspended:
        return 'Suspended'
    if admin:
        return 'Administrator'
    return ''

def _get_or_empty(x, attr):
    try:
        return x[attr]
    except:
        try:
            return getattr(x, attr)
        except:
            return ''

_userFields = [
    Column('Name', 'name', getter=_get_name),
    Column('Username', 'user_name', id=True),
    Column('Status', 'status', getter=_get_status),
    Column('Email quota', 'quota', getter=lambda x: _get_or_empty(x, 'quota')),
    Column('Roles', 'roles', getter=lambda x: _get_or_empty(x, 'roles')),
    Column('Last signed in', 'last_login', getter=lambda x: _get_or_empty(x, 'last_login'))
]

_groupFields = [
    Column('Name', 'name'),
    Column('Email address', 'email', id=True),
    Column('Type', 'type'),
]

_userWidths = [
    '5%', '15%', '25%', '15%', '15%', '15%', '10%'
]

_groupWidths = [
    '5%', '40%', '40%', '15%'
]

class UserForm(forms.Form):
    user_name = forms.CharField(label='Username')
    given_name = forms.CharField(label='Given name')
    family_name = forms.CharField(label='Family name')
    suspended = forms.BooleanField(label='Account suspended', required=False)
    admin = forms.BooleanField(label='Privileges', required=False, help_text='Administrators can manage all users and settings for this domain')

def _get_sortby_asc(request, valid):
    sortby = request.GET.get('sortby', valid[0])
    asc = (request.GET.get('asc', 'true') == 'true')
    if not sortby in valid:
        sortby = valid[0]
    return (sortby, asc)

def users(request):
    sortby, asc = _get_sortby_asc(request, [f.name for f in _userFields])
    
    _users = GAUser.all().fetch(100)
    
    table = Table(_userFields, sortby=sortby, asc=asc)
    table.sort(_users)
    
    return render_to_response('users_list.html', {'table': table.generate(_users, _userWidths)})

def user(request, name=None):
    if name == None:
        return redirect('..')
    
    _user = GAUser.get_by_key_name(name)
    
    if request.method == 'POST':
        form = UserForm(request.POST, auto_id=True)
        if form.is_valid():
            return redirect('crgappspanel.views.user', name=name)
    else:
        form = UserForm(initial={
            'given_name': _user.given_name,
            'family_name': _user.family_name,
            'suspernded': _user.suspended,
            'admin': _user.admin,
        }, auto_id=True)
    
    return render_to_response('user_details.html', {
        'name': name,
        'given_name': _user.given_name,
        'family_name': _user.family_name,
        'form': form
    })

def groups(request):
    sortby, asc = _get_sortby_asc(request, [f.name for f in _groupFields])
    
    table = Table(_groupFields, sortby=sortby, asc=asc)
    table.sort(_groups)
    
    return render_to_response('groups_list.html', {'table': table.generate(_groups, _groupWidths)})

def test(request):
    users = GAUser.all().fetch(100)
    
    res = ''
    for i in range(len(users)):
        res += 'users[%d]:\n' % i
        for field_name in ['given_name', 'family_name', 'user_name', 'password', 'suspended', 'admin']:
            field_value = getattr(users[i], field_name)
            res += '  %s: %s [%s]\n' % (field_name, field_value, str(type(field_value)))
        res += '\n'
    res += '\n'
    
    return HttpResponse(res, mimetype='text/plain')
