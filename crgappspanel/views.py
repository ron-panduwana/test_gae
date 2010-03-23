from django import forms
from django.http import HttpResponse
from django.shortcuts import render_to_response, redirect
from crgappspanel.tables import Table, Column
from crgappspanel.models import GAUser, GANickname
from crgappspanel.sample_data import get_sample_groups

def _get_prop(obj, prop, default=None):
    try:
        return obj[prop]
    except:
        if default != None:
            try:
                return getattr(obj, prop)
            except:
                return default
        else:
            return getattr(obj, prop)

def _get_name(x):
    given_name, family_name = _get_prop(x, 'given_name'), _get_prop(x, 'family_name')
    return '%s %s' % (given_name, family_name)

def _get_status(x):
    suspended, admin = _get_prop(x, 'suspended'), _get_prop(x, 'admin')
    return 'Suspended' if suspended else 'Administrator' if admin else ''

_userFields = [
    Column('Name', 'name', getter=_get_name),
    Column('Username', 'user_name', id=True),
    Column('Status', 'status', getter=_get_status),
    Column('Email quota', 'quota', getter=lambda x: _get_prop(x, 'quota', default='')),
    Column('Roles', 'roles', getter=lambda x: _get_prop(x, 'roles', default='')),
    Column('Last signed in', 'last_login', getter=lambda x: _get_prop(x, 'last_login', default=''))
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
    
    table = Table(_userFields, sortby=sortby, asc=asc)
    table.sort(users)
    
    return render_to_response('users_list.html', {'table': table.generate(users, _userWidths)})

def user(request, name=None):
    if name == None:
        return redirect('..')
    
    user = GAUser.get_by_key_name(name)
    
    if request.method == 'POST':
        form = UserForm(request.POST, auto_id=True)
        if form.is_valid():
            return redirect('crgappspanel.views.user', name=name)
    else:
        form = UserForm(initial={
            'given_name': user.given_name,
            'family_name': user.family_name,
            'suspernded': user.suspended,
            'admin': user.admin,
        }, auto_id=True)
    
    return render_to_response('user_details.html', {
        'name': name,
        'given_name': user.given_name,
        'family_name': user.family_name,
        'form': form
    })

def groups(request):
    sortby, asc = _get_sortby_asc(request, [f.name for f in _groupFields])
    
    groups = get_sample_groups()
    table = Table(_groupFields, sortby=sortby, asc=asc)
    table.sort(groups)
    
    return render_to_response('groups_list.html', {'table': table.generate(groups, _groupWidths)})

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

