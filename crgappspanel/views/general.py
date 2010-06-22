from django.http import HttpResponse
from django.shortcuts import redirect

import crauth
from crauth import users
from crauth.decorators import login_required
from crgappspanel.models import GAUser, GAGroup
from crlib.navigation import render_with_nav


@login_required
def dashboard(request):
    return render_with_nav(request, 'dashboard.html')


@login_required
def feedback_thanks(request):
    return render_with_nav(request, 'feedback_thanks.html')


def language(request):
    return render(request, 'language.html', {'LANGUAGES': LANGUAGES})


@login_required
def test(request):
    from crauth.models import AppsDomain, Role, UserPermissions
    
    email = 'bbking@moroccanholidayrental.com'
    role_names = ['User creator']
    
    perms = UserPermissions.get_or_insert(key_name=email, user_email=email)
    for role_name in role_names:
        role = Role.for_domain(users.get_current_domain()).filter('name', role_name).get()
        perms.roles.append(role.key())
    perms.save()
    
    sth = str(perms)
    
    return render_with_nav(request, 'test.html', {
        'sth': sth,
    })
