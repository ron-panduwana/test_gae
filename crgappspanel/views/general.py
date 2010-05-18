from django.http import HttpResponse
from django.shortcuts import redirect

import crauth
from crauth import users
from crauth.decorators import login_required
from crgappspanel.models import GAGroup
from crlib.navigation import render_with_nav


def index(request):
    return redirect('users')


def language(request):
    return render(request, 'language.html', {'LANGUAGES': LANGUAGES})


@login_required
def test(request):
    from crauth.models import AppsDomain, Role
    
    domain = AppsDomain.get_by_key_name(users.get_current_user().domain_name)
    perms = ['add_gauser', 'change_gauser', 'read_gauser']
    
    Role(name='User manager', permissions=perms, domain=domain).save()
    sth = 'domain name: ' + users.get_current_user().domain_name + '\n'
    sth += 'domain: ' + str(domain) + '\n'
    sth += 'admin perms: ' + str(crauth.permissions.ADMIN_PERMS) + '\n'
    sth += 'permission choices: ' + str(crauth.permissions.permission_choices()) + '\n'
    sth += 'permission choices (no admin): ' + str(crauth.permissions.permission_choices(False)) + '\n'
    return render_with_nav(request, 'test.html', {
        'sth': sth,
        #'scripts': ['test'],
    })
