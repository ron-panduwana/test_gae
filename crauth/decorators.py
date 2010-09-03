import logging
import urllib
from functools import wraps
from django.http import HttpResponseRedirect
from django.conf import settings
from django.core.urlresolvers import reverse
from crgappspanel import models
from crlib.navigation import render_with_nav
from crlib.models import GDataIndex
from crlib.cache import MIN_DATETIME
from crauth import users


def admin_required(func):
    """Decorator. Makes sure current user is logged in and is domain
    administrator.
    
    Redirects to admin_required page otherwise.

    """
    @wraps(func)
    def new(request, *args, **kwargs):
        if users.is_current_user_admin():
            return func(request, *args, **kwargs)
        return HttpResponseRedirect(reverse('admin_required'))
    new.perm_list = ['admin']
    return new


GOOGLE_APPS_LOGOUT_URL = 'https://www.google.com/a/cpanel/%s/cpanelLogout'
def login_required(func):
    """Decorator. Makes sure current user is logged in.
    
    Redirects to login page otherwise.

    """
    @wraps(func)
    def new(request, *args, **kwargs):
        # TODO: check if user is licensed to use the application
        user = users.get_current_user()
        if user:
            logout_url = GOOGLE_APPS_LOGOUT_URL % user.domain_name
            if user.is_deleted:
                return HttpResponseRedirect(logout_url)
            ga_user = models.GAUser.all().filter(
                'user_name', user.nickname()).get()
            if not ga_user:
                ga_user = models.GAUser.get_by_key_name(
                    user.nickname(), cached=False)
            if ga_user:
                return func(request, *args, **kwargs)
            else:
                index = GDataIndex.get_by_key_name(
                    '%s:%s' % (user.domain_name, 'GAUser'))
                if index and index.last_updated > MIN_DATETIME:
                    return HttpResponseRedirect(logout_url)
                else:
                    return HttpResponseRedirect(
                        reverse('cache_not_ready') + '?' +
                        urllib.urlencode({
                            settings.REDIRECT_FIELD_NAME:
                            request.get_full_path()}))
        return HttpResponseRedirect(
            users.create_login_url(request.get_full_path()))
    return new


def has_perm(perm):
    def decorator(func):
        @wraps(func)
        @login_required
        def new(request, *args, **kwargs):
            if users.get_current_user().has_perm(perm):
                return func(request, *args, **kwargs)
            return render_with_nav(request, 'not_authorized.html')
        new.perm_list = [perm]
        return new
    return decorator


def has_perms(perm_list):
    def decorator(func):
        @wraps(func)
        @login_required
        def new(request, *args, **kwargs):
            if users.get_current_user().has_perms(perm_list):
                return func(request, *args, **kwargs)
            return render_with_nav(request, 'not_authorized.html')
        new.perm_list = perm_list
        return new
    return decorator

