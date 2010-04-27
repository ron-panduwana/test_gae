import logging
import os
import urllib
from django.conf import settings
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from django import forms
from google.appengine.api import memcache
from gdata.service import GDataService, CaptchaRequired, BadAuthentication
from gdata.client import GDClient, CaptchaChallenge
from gdata.gauth import ClientLoginToken, TwoLeggedOAuthHmacToken
from gdata.apps.service import AppsForYourDomainException
from settings import APPS_DOMAIN, CLIENT_LOGIN_SOURCE


_SESSION_LOGIN_INFO = '_client_login_info'
_SERVICE_MEMCACHE_TOKEN_KEY = 'service_client_login_token:%s:%s'
_CLIENT_MEMCACHE_TOKEN_KEY = 'client_client_login_token:%s:%s'
_ENVIRON_EMAIL = 'CLIENT_LOGIN_EMAIL'
_ENVIRON_PASWD = 'CLIENT_LOGIN_PASWD'


class LoginRequiredError(Exception): pass


class User(object):
    def __init__(self, email, password):
        self._email = email
        self._password = password

    def nickname(self):
        return self._email.partition('@')[0]

    def email(self):
        return self._email

    def domain(self):
        return self._email.partition('@')[2]

    def _client_login_service(self, service):
        memcache_key = _SERVICE_MEMCACHE_TOKEN_KEY % (
            self._email, service.service)
        token = memcache.get(memcache_key)
        if not token:
            service.email = self._email
            service.password = self._password
            try:
                service.ProgrammaticLogin()
            except CaptchaRequired:
                challenge = CaptchaChallenge('CAPTCHA Required')
                challenge.captcha_url = service.captcha_url
                challenge.captcha_token = service.captcha_token
                challenge.service = service.service
                challenge.is_old_api = True
                raise challenge
            except Exception:
                raise LoginRequiredError()
            token = service.GetClientLoginToken()
            memcache.set(memcache_key, token, 24 * 60 * 60)
        else:
            service.SetClientLoginToken(token)

    def _client_login_client(self, client):
        memcache_key = _CLIENT_MEMCACHE_TOKEN_KEY % (
            self._email, client.auth_service)
        token = memcache.get(memcache_key)
        if not token:
            try:
                client.client_login(
                    self._email, self._password, CLIENT_LOGIN_SOURCE)
            except CaptchaChallenge, challenge:
                challenge.service = client.auth_service
                challenge.is_old_api = False
                raise challenge
            except Exception:
                raise LoginRequiredError()
            token = client.auth_token.token_string
            memcache.set(memcache_key, token, 24 * 60 * 60)
        else:
            client.auth_token = ClientLoginToken(token)

    def client_login(self, service):
        if isinstance(service, GDataService):
            if service.GetClientLoginToken() is None:
                self._client_login_service(service)
        elif isinstance(service, GDClient):
            if service.auth_token is None:
                self._client_login_client(service)
        else:
            raise Exception('Unknown service type: %s' %
                            service.__class__.__name__)

    def oauth_login(self, client):
        if client.auth_token is None:
            client.auth_token = TwoLeggedOAuthHmacToken(
                settings.OAUTH_CONSUMER,
                settings.OAUTH_SECRET,
                settings.OAUTH_REQUESTOR_ID)


class UsersMiddleware(object):
    def process_request(self, request):
        client_login_info = request.session.get(_SESSION_LOGIN_INFO)
        if not client_login_info or client_login_info.has_key('captcha_token'):
            return
        os.environ[_ENVIRON_EMAIL] = client_login_info['email']
        os.environ[_ENVIRON_PASWD] = client_login_info['password']

    def process_exception(self, request, exception):
        if isinstance(exception, LoginRequiredError):
            request.session.flush()
            return HttpResponseRedirect(
                create_login_url(request.get_full_path()))
        elif isinstance(exception, CaptchaChallenge):
            client_login_info = request.session.get(_SESSION_LOGIN_INFO, {})
            client_login_info['captcha_url'] = exception.captcha_url
            client_login_info['captcha_token'] = exception.captcha_token
            client_login_info['service'] = exception.service
            client_login_info['is_old_api'] = exception.is_old_api
            request.session[_SESSION_LOGIN_INFO] = client_login_info
            return HttpResponseRedirect(
                create_login_url(request.get_full_path()))
        elif isinstance(exception, AppsForYourDomainException):
            logging.warning('exception: %s' % str(exception))
            return None


class LoginForm(forms.Form):
    user_name = forms.CharField(required=True)
    password = forms.CharField(required=True, widget=forms.PasswordInput)
    captcha_token = forms.CharField(required=False, widget=forms.HiddenInput)
    captcha_url = forms.CharField(required=False, widget=forms.HiddenInput)
    catpcha_service = forms.CharField(
        required=False, widget=forms.HiddenInput, initial='apps')
    is_old_api = forms.BooleanField(
        required=False, widget=forms.HiddenInput, initial=True)
    captcha = forms.CharField(required=False)

    def __init__(self, *args, **kwargs):
        super(LoginForm, self).__init__(*args, **kwargs)

    def clean_captcha(self):
        captcha = self.cleaned_data['captcha']
        if self.cleaned_data['captcha_token'] and not captcha:
            raise forms.ValidationError('You have to type captcha')
        return captcha

    def _client_login_service(self, email, service_name):
        service = GDataService(
            email=email,
            password=self.cleaned_data['password'],
            service=service_name)
        try:
            service.ProgrammaticLogin(
                self.cleaned_data['captcha_token'] or None,
                self.cleaned_data['captcha'] or None)
        except CaptchaRequired:
            self.data = self.data.copy()
            self.data['captcha_token'] = service.captcha_token
            self.data['captcha_url'] = service.captcha_url
            raise forms.ValidationError('Please provide CAPTCHA')
        except Exception, e:
            raise forms.ValidationError(e.message)

        memcache.set(_SERVICE_MEMCACHE_TOKEN_KEY % (email, captcha_service),
                     service.GetClientLoginToken(), 24 * 60 * 60)

    def _client_login_client(self, email, service_name):
        client = GDClient()
        try:
            client.client_login(email, self.cleaned_data['password'],
                                CLIENT_LOGIN_SOURCE)
        except CaptchaChallenge, challenge:
            self.data = self.data.copy()
            self.data['captcha_token'] = challenge.captcha_token
            self.data['captcha_url'] = challenge.captcha_url
            raise forms.ValidationError('Please provide CAPTCHA')
        except Exception, e:
            raise forms.ValidationError(e.message)

        memcache.set(_CLIENT_MEMCACHE_TOKEN_KEY % (email, captcha_service),
                     service.auth_token.token_string, 24 * 60 * 60)

    def clean(self):
        if self._errors:
            return self.cleaned_data

        captcha_service = self.cleaned_data.get('captcha_service')
        if not captcha_service:
            return self.cleaned_data

        email='%s@%s' % (self.cleaned_data['user_name'], APPS_DOMAIN)

        if self.cleaned_data['is_old_api']:
            self._client_login_service(email, captcha_service)
        else:
            self._client_login_client(email, captcha_service)

        return self.cleaned_data


def generic_login_view(request, template):
    redirect_to = request.GET.get(
        'redirect_to', request.META.get('HTTP_REFERER', '/'))
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            email = '%s@%s' % (form.cleaned_data['user_name'], APPS_DOMAIN)
            request.session[_SESSION_LOGIN_INFO] = {
                'domain': APPS_DOMAIN,
                'email': email,
                'password': form.cleaned_data['password'],
            }
            return HttpResponseRedirect(redirect_to)
        logging.warning('form: %s' % str(form))
    else:
        client_login_info = request.session.get(_SESSION_LOGIN_INFO)
        if client_login_info:
            initial = {
                'user_name': client_login_info['email'].partition('@')[0],
                'captcha_token': client_login_info.get('captcha_token'),
                'captcha_url': client_login_info.get('captcha_url'),
                'captcha_service': client_login_info.get('service', 'apps'),
                'is_old_api': client_login_info.get('is_old_api', True),
            }
            form = LoginForm(initial=initial)
        else:
            form = LoginForm()
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
        return HttpResponseRedirect(create_login_url(request.get_full_path()))
    new.__name__ = func.__name__
    new.__doc__ = func.__doc__
    return new


def create_login_url(dest_url):
    return reverse(generic_login_view) + '?%s' % urllib.urlencode({
        'redirect_to': dest_url})


def create_logout_url(dest_url):
    return reverse(generic_logout_view) + '?%s' % urllib.urlencode({
        'redirect_to': dest_url})


def get_current_user():
    if os.environ.has_key(_ENVIRON_PASWD):
        return User(
            os.environ[_ENVIRON_EMAIL],
            os.environ[_ENVIRON_PASWD])
    else:
        return None


def is_current_user_admin():
    return os.environ.has_key(_ENVIRON_PASWD)


def _set_testing_user(email, password):
    os.environ[_ENVIRON_EMAIL] = email
    os.environ[_ENVIRON_PASWD] = password

