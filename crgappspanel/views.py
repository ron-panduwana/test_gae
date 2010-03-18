from django.shortcuts import render_to_response, get_object_or_404

def users(request):
    if 'sortby' in request.GET:
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
    
    objects.sort(compare)
    
    return render_to_response('users_list.html', {'objects': objects, 'sortby': sortby, 'asc': asc})
