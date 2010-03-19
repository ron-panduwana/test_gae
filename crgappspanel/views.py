from django.shortcuts import render_to_response, get_object_or_404
from crgappspanel.tables import Table, Field

_users = [
    {
        'name': 'Pawel Zaborski',
        'username': 'pawel@moroccanholidayrental.com',
        'status': 'Administrator',
        'quota': '0% of 25 GB',
        'roles': 'admin',
        'last_login': '9:28 pm',
    },
    {
        'name': 'Roland Plaszowski',
        'username': 'roland@moroccanholidayrental.com',
        'status': 'Administrator',
        'quota': '0% of 25 GB',
        'roles': 'admin',
        'last_login': 'Jan 6',
    },
    {
        'name': 'Kamil Klimkiewicz',
        'username': 'kamil@moroccanholidayrental.com',
        'status': '',
        'quota': '0% of 25 GB',
        'roles': 'admin',
        'last_login': '3:15 pm',
    },
    {
        'name': 'sky mail',
        'username': 'skymail@moroccanholidayrental.com',
        'status': '',
        'quota': '3% of 25 GB',
        'roles': 'sample',
        'last_login': 'Mar 15',
    },
#    {
#        'name': 'google user',
#        'username': users[0].user_name,
#        'status': '',
#        'quota': '3% of 25 GB',
#        'roles': 'sample',
#        'last_login': 'Mar 15',
#    },
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

_userFields = [
    Field('name', 'Name'),
    Field('username', 'Username'),
    Field('status', 'Status'),
    Field('quota', 'Email quota'),
    Field('roles', 'Roles'),
    Field('last_login', 'Last signed in')
]

_groupFields = [
    Field('name', 'Name'),
    Field('email', 'Email address'),
    Field('type', 'Type'),
]

_userWidths = [
    '5%', '15%', '25%', '15%', '15%', '15%', '10%'
]

_groupWidths = [
    '5%', '40%', '40%', '15%'
]

def _get_sortby_asc(request, valid):
    sortby = request.GET.get('sortby', valid[0])
    asc = (request.GET.get('asc', 'true') == 'true')
    if sortby in valid:
        return (sortby, asc)
    else:
        return (valid[0], asc)

def users(request):
    sortby, asc = _get_sortby_asc(request, [f.name for f in _userFields])
    
    table = Table(_userFields, sortby=sortby, asc=asc)
    table.sort(_users)
    
    ctx = {
        'table': table.generate(_users),
        'widths': _userWidths,
    }
    return render_to_response('users_list.html', ctx)

def groups(request):
    sortby, asc = _get_sortby_asc(request, [f.name for f in _groupFields])
    
    table = Table(_groupFields, sortby=sortby, asc=asc)
    print _groups
    table.sort(_groups)
    
    ctx = {
        'table': table.generate(_groups),
        'widths': _groupWidths,
    }
    return render_to_response('groups_list.html', ctx)
