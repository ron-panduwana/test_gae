import logging
from functools import wraps
from django.http import HttpResponseRedirect
from crlib.navigation import render_with_nav
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
    return new


def login_required(func):
    """Decorator. Makes sure current user is logged in.
    
    Redirects to login page otherwise.

    """
    @wraps(func)
    def new(request, *args, **kwargs):
        # TODO: check if user is licensed to use the application
        if users.get_current_user() is not None:
            return func(request, *args, **kwargs)
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

