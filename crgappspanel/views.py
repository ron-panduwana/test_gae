from django.shortcuts import render_to_response, get_object_or_404
from crgappspanel.tables import Table, Field

objects = [
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
]

fields = [
    Field('name', 'Name'),
    Field('username', 'Username'),
    Field('status', 'Status'),
    Field('quota', 'Email quota'),
    Field('roles', 'Roles'),
    Field('last_login', 'Last signed in')
]
widths = [
    '5%', '15%', '25%', '15%', '15%', '15%', '10%'
]
fieldNames = [field.name for field in fields]

def users(request):
    if ('sortby' in request.GET) and (request.GET['sortby'] in fieldNames):
        sortby = request.GET['sortby']
    else:
        sortby = 'name'
    asc = not ('asc' in request.GET) or (request.GET['asc'] == 'true')
    
    def compare(x, y):
        xx = x[sortby]
        yy = y[sortby]
        if xx < yy:
            if asc:
                return -1
            else:
                return 1
        elif xx > yy:
            if asc:
                return 1
            else:
                return -1
        else:
            return 0
    
    objects.sort(compare)
    
    table = Table(fields, widths, select=True, sortby=sortby, asc=asc, html_width='100%', css_class='data')
    
    return render_to_response('users_list.html', {'table_js': table.gen_js(objects), 'table_html': table.gen_html(objects)})
