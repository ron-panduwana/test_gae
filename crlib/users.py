import logging
import os
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from django import forms
from google.appengine.api import memcache
from gdata.service import GDataService, CaptchaRequired, BadAuthentication
from settings import APPS_DOMAIN


_SESSION_LOGIN_INFO = '_client_login_info'
_MEMCACHE_TOKEN_KEY = 'client_login_token:%s'
_ENVIRON_EMAIL = 'CLIENT_LOGIN_EMAIL'
_ENVIRON_TOKEN = 'CLIENT_LOGIN_TOKEN'


class LoginRequiredError(Exception): pass


class User(object):
    def __init__(self, email, client_login_token=None):
        self._email = email
        self._client_login_token = client_login_token

    def nickname(self):
        return self._email.partition('@')[0]

    def email(self):
        return self._email

    def domain(self):
        return self._email.partition('@')[2]

    def client_login_token(self):
        return self._client_login_token


class UsersMiddleware(object):
    def process_request(self, request):
        client_login_info = request.session.get(_SESSION_LOGIN_INFO)
        if not client_login_info or client_login_info.has_key('captcha_token'):
            return
        memcache_key = _MEMCACHE_TOKEN_KEY % client_login_info['email']
        token = memcache.get(memcache_key)
        if not token:
            service = GDataService(
                email=client_login_info['email'],
                password=client_login_info['password'],
                service='apps')
            try:
                service.ProgrammaticLogin()
            except CaptchaRequired:
                client_login_info.update({
                    'captcha_token': service.captcha_token,
                    'captcha_url': service.captcha_url,
                })
                request.session[_SESSION_LOGIN_INFO] = client_login_info
                return
            except BadAuthentication:
                request.session.flush()
                return
            token = service.GetClientLoginToken()
            memcache.set(memcache_key, token, 24 * 60 * 60)
        os.environ[_ENVIRON_EMAIL] = client_login_info['email']
        os.environ[_ENVIRON_TOKEN] = token

    def process_exception(self, request, exception):
        if isinstance(exception, LoginRequiredError):
            return HttpResponseRedirect(create_login_url(request.path))


class _LoginForm(forms.Form):
    user_name = forms.CharField(required=True)
    password = forms.CharField(required=True, widget=forms.PasswordInput)
    captcha_token = forms.CharField(required=False, widget=forms.HiddenInput)
    captcha_url = forms.CharField(required=False, widget=forms.HiddenInput)
    captcha = forms.CharField(required=False)

    def __init__(self, *args, **kwargs):
        super(_LoginForm, self).__init__(*args, **kwargs)

    def clean_captcha(self):
        captcha = self.cleaned_data['captcha']
        if self.cleaned_data['captcha_token'] and not captcha:
            raise forms.ValidationError('You have to type captcha')
        return captcha

    def clean(self):
        if self._errors:
            return self.cleaned_data

        service = GDataService(
            email='%s@%s' % (self.cleaned_data['user_name'], APPS_DOMAIN),
            password=self.cleaned_data['password'],
            service='apps')

        try:
            service.ProgrammaticLogin(
                self.cleaned_data['captcha_token'] or None,
                self.cleaned_data['captcha'] or None)
        except CaptchaRequired:
            self.data = self.data.copy()
            self.data['captcha_token'] = service.captcha_token
            self.data['captcha_url'] = service.captcha_url
            raise forms.ValidationError('Please provide captcha')
        except BadAuthentication, e:
            raise forms.ValidationError(e.message)

        self.token = service.GetClientLoginToken()

        return self.cleaned_data


def generic_login_view(request, template):
    redirect_to = request.GET.get(
        'redirect_to', request.META.get('HTTP_REFERER', '/'))
    if request.method == 'POST':
        form = _LoginForm(request.POST)
        if form.is_valid():
            email = '%s@%s' % (form.cleaned_data['user_name'], APPS_DOMAIN)
            request.session[_SESSION_LOGIN_INFO] = {
                'domain': APPS_DOMAIN,
                'email': email,
                'password': form.cleaned_data['password'],
            }
            memcache.set(_MEMCACHE_TOKEN_KEY % email,
                         form.token, 24 * 60 * 60)
            return HttpResponseRedirect(redirect_to)
    else:
        client_login_info = request.session.get(_SESSION_LOGIN_INFO)
        if client_login_info:
            initial = {
                'user_name': client_login_info['email'].partition('@')[0],
                'captcha_token': client_login_info.get('captcha_token'),
                'captcha_url': client_login_info.get('captcha_url'),
            }
            form = _LoginForm(initial=initial)
        else:
            form = _LoginForm()
    ctx = {
        'form': form,
        'domain': APPS_DOMAIN,
    }
    return render_to_response(template, ctx)


def generic_logout_view(request):
    redirect_to = request.GET.get(
        'redirect_to', request.META.get('HTTP_REFERER', '/'))
    try:
        request.session.flush()
    except TypeError:
        pass
    return HttpResponseRedirect(redirect_to)


def admin_required(func):
    """Decorator. Makes sure current user is logged in and is administrator.
    
    Redirects to login page otherwise.

    """
    def new(request, *args, **kwargs):
        if is_current_user_admin():
            return func(request, *args, **kwargs)
        return HttpResponseRedirect(create_login_url(request.path))
    new.__name__ = func.__name__
    new.__doc__ = func.__doc__
    return new


def create_login_url(dest_url):
    return reverse(generic_login_view) + '?redirect_to=%s' % dest_url


def create_logout_url(dest_url):
    return reverse(generic_logout_view) + '?redirect_to=%s' % dest_url


def get_current_user():
    if os.environ.has_key(_ENVIRON_TOKEN):
        return User(
            os.environ[_ENVIRON_EMAIL],
            os.environ[_ENVIRON_TOKEN])
    else:
        return None


def is_current_user_admin():
    return os.environ.has_key(_ENVIRON_TOKEN)


def _set_testing_user(email, password):
    service = GDataService(
        email=email,
        password=password,
        service='apps')
    service.ProgrammaticLogin()
    token = service.GetClientLoginToken()
    memcache.set(_MEMCACHE_TOKEN_KEY % email, token, 24 * 60 * 60)
    os.environ[_ENVIRON_EMAIL] = email
    os.environ[_ENVIRON_TOKEN] = token

