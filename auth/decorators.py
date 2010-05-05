from django.http import HttpResponseRedirect
from auth import users


def admin_required(func):
    """Decorator. Makes sure current user is logged in and is domain
    administrator.
    
    Redirects to admin_required page otherwise.

    """
    def new(request, *args, **kwargs):
        if users.is_current_user_admin():
            return func(request, *args, **kwargs)
        return HttpResponseRedirect(reverse('admin_required'))
    new.__name__ = func.__name__
    new.__doc__ = func.__doc__
    return new


def login_required(func):
    """Decorator. Makes sure current user is logged in.
    
    Redirects to login page otherwise.

    """
    def new(request, *args, **kwargs):
        # TODO: check if user is licensed to use the application
        if users.get_current_user() is not None:
            return func(request, *args, **kwargs)
        return HttpResponseRedirect(
            users.create_login_url(request.get_full_path()))
    new.__name__ = func.__name__
    new.__doc__ = func.__doc__
    return new


