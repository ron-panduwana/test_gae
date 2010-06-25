from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect

import crauth
from crauth import users
from crauth.decorators import login_required
from crgappspanel.views.utils import redirect_saved
from crgappspanel.models import Preferences, GAUser, GAGroup
from crgappspanel import forms
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
def settings(request):
    prefs = Preferences.for_current_user()

    if request.method == 'POST':
        if '_cancel' in request.POST:
            return HttpResponseRedirect(request.path)

        form = forms.SettingsForm(request.POST, instance=prefs)

        if form.is_valid():
            form.save()
            return redirect_saved('settings', request)

    form = forms.SettingsForm(instance=prefs)
    ctx = {
        'form': form,
        'saved': request.session.pop('saved', False),
    }
    return render_with_nav(request, 'settings.html', ctx)


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
