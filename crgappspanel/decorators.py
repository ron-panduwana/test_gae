import os
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from google.appengine.api import memcache
from crgappspanel.forms import LoginForm


CLIENT_LOGIN_INFO = 'client_login_info'
CLIENT_LOGIN_TOKEN_KEY = 'client_login_token:%s'


def admin_required(func):
    def new(request, *args, **kwargs):
        redirect_to = '?redirect_to=%s' % request.path
        client_login_info = request.session.get(CLIENT_LOGIN_INFO)
        if client_login_info:
            memcache_key = CLIENT_LOGIN_TOKEN_KEY % client_login_info['email']
            token = memcache.get(memcache_key)
            if not token:
                form = LoginForm({
                    'user_name': client_login_info['email'].partition('@')[0],
                    'password': client_login_info['password'],
                })
                if not form.is_valid():
                    return HttpResponseRedirect(reverse('login') + redirect_to)
                token = form.token
                memcache.set(memcache_key, token, 24 * 60 * 60)
            os.environ['CLIENT_LOGIN_DOMAIN'] = client_login_info['domain']
            os.environ['CLIENT_LOGIN_TOKEN'] = token
            return func(request, *args, **kwargs)
        else:
            return HttpResponseRedirect(reverse('login') + redirect_to)
    new.__name__ = func.__name__
    new.__doc__ = func.__doc__
    return new

