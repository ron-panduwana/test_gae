import logging
import os
import pickle
import urllib
from django.conf import settings
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from django import forms
from google.appengine.ext import db
from google.appengine.api import memcache
from gdata.service import GDataService, CaptchaRequired, BadAuthentication
from gdata.client import GDClient, CaptchaChallenge
from gdata.gauth import ClientLoginToken, TwoLeggedOAuthHmacToken
from gdata.apps.service import AppsForYourDomainException
from crauth.models import AppsDomain, UserPermissions, Role
from crauth.permissions import ADMIN_PERMS


_SERVICE_MEMCACHE_TOKEN_KEY = 'service_client_login_token:%s:%s'
_CLIENT_MEMCACHE_TOKEN_KEY = 'client_client_login_token:%s:%s'
_ENVIRON_EMAIL = 'CLIENT_LOGIN_EMAIL'
_ENVIRON_DOMAIN = 'CLIENT_LOGIN_DOMAIN'


class LoginRequiredError(Exception): pass
class SetupRequiredError(Exception): pass


class User(object):
    def __init__(self, email, domain):
        self._email = email.lstrip('*')
        self.is_deleted = email.startswith('*')
        self.domain_name = domain

    def nickname(self):
        return self._email.partition('@')[0]

    def email(self):
        """Returns email address of given User."""
        return self._email

    def domain(self):
        """Returns :class:`AppsDomain <crauth.models.AppsDomain>` object the
        User is part of.

        """
        return AppsDomain.get_by_key_name(self.domain_name)

    def _client_login_service(self, service, captcha_token, captcha):
        memcache_key = _SERVICE_MEMCACHE_TOKEN_KEY % (
            self.domain_name, service.service)
        token = memcache.get(memcache_key)
        if not token:
            from gdata.service import BadAuthentication
            apps_domain = self.domain()
            if apps_domain is None:
                raise SetupRequiredError()
            service.email = apps_domain.admin_email
            service.password = apps_domain.admin_password
            try:
                service.ProgrammaticLogin(captcha_token, captcha)
            except CaptchaRequired:
                challenge = CaptchaChallenge('CAPTCHA Required')
                challenge.captcha_url = service.captcha_url
                challenge.captcha_token = service.captcha_token
                challenge.service = service
                raise challenge
            except BadAuthentication:
                raise SetupRequiredError()
            token = service.GetClientLoginToken()
            memcache.set(memcache_key, token, 24 * 60 * 60)
        else:
            service.SetClientLoginToken(token)

    def _client_login_client(self, client, captcha_token, captcha):
        memcache_key = _CLIENT_MEMCACHE_TOKEN_KEY % (
            self.domain_name, client.auth_service)
        token = memcache.get(memcache_key)
        if not token:
            from gdata.client import BadAuthentication
            apps_domain = self.domain()
            if apps_domain is None:
                raise SetupRequiredError()
            email = apps_domain.admin_email
            password = apps_domain.admin_password
            try:
                client.client_login(
                    email, password, settings.CLIENT_LOGIN_SOURCE,
                    captcha_token=captcha_token, captcha_response=captcha)
            except CaptchaChallenge, challenge:
                challenge.service = client
                raise challenge
            except BadAuthentication:
                raise SetupRequiredError()
            token = client.auth_token.token_string
            memcache.set(memcache_key, token, 24 * 60 * 60)
        else:
            client.auth_token = ClientLoginToken(token)

    def client_login(self, service, captcha_token=None, captcha=None):
        if isinstance(service, GDataService):
            if service.GetClientLoginToken() is None:
                self._client_login_service(service, captcha_token, captcha)
        elif isinstance(service, GDClient):
            if service.auth_token is None:
                self._client_login_client(service, captcha_token, captcha)
        else:
            raise Exception('Unknown service type: %s' %
                            service.__class__.__name__)

    def oauth_login(self, client):
        if client.auth_token is None:
            client.auth_token = TwoLeggedOAuthHmacToken(
                settings.OAUTH_CONSUMER,
                settings.OAUTH_SECRET,
                self.email())

    def is_admin(self):
        """Checks if given User is an administrator of its *Google Apps* domain.
        
        This check is performed using *GData API* with the help of *OAuth*
        2-legged authentication method. For this method to work we need access
        to *Provisioning API* for given domain.

        :returns: ``True`` or ``False``.

        """
        from gdata.apps.service import AppsService
        from gdata.auth import OAuthSignatureMethod
        is_admin = memcache.get(self.email(), namespace='is_current_user_admin')
        if is_admin is not None:
            return is_admin
        service = AppsService(domain=self.domain_name)
        service.SetOAuthInputParameters(
            OAuthSignatureMethod.HMAC_SHA1,
            settings.OAUTH_CONSUMER, settings.OAUTH_SECRET,
            two_legged_oauth=True)
        service.debug = True
        username = self.email().rpartition('@')[0]
        try:
            apps_user = service.RetrieveUser(username)
        except AppsForYourDomainException:
            try:
                service = AppsService(domain=self.domain_name)
                self.client_login(service)
                apps_user = service.RetrieveUser(username)
            except (SetupRequiredError, CaptchaChallenge):
                return False
        is_admin = apps_user is not None and apps_user.login.admin == 'true'
        memcache.set(self.email(), is_admin, 60 * 60,
                     namespace='is_current_user_admin')
        return is_admin

    def has_perm(self, permission):
        """Returns ``True`` if the User has permission ``permission``.

        It simply calls :func:`has_perms` with ``[permission]`` argument.
        
        """
        return self.has_perms([permission])

    def has_perms(self, perm_list):
        """Returns ``True`` if the User has all of the permissions in the
        ``perm_list`` list.

        This method always returns ``True`` if :func:`is_admin` returns
        ``True``.

        On the other hand, it always returns ``False`` if ``perm_list`` contains
        permission from :attr:`ADMIN_PERMS <crauth.permissions.ADMIN_PERMS>` and
        :func:`is_admin` returns ``False``.

        """
        perm_list = set(perm_list)
        is_admin = self.is_admin()
        if is_admin:
            return True

        if perm_list.intersection(set(ADMIN_PERMS)):
            return is_admin

        permissions = UserPermissions.get_or_insert(
            key_name=self._email,
            user_email=self._email)
        if not permissions:
            return False
        roles = [role for role in Role.get(permissions.roles) if role]
        all_perms = set(permissions.permissions)
        for role in roles:
            all_perms.update(role.permissions)
        return all_perms.issuperset(perm_list)


class UsersMiddleware(object):
    def process_request(self, request):
        client_login_info = request.session.get(settings.SESSION_LOGIN_INFO_KEY)
        if not client_login_info or \
           not client_login_info.has_key('email'):
            if os.environ.has_key(_ENVIRON_EMAIL):
                del os.environ[_ENVIRON_EMAIL]
            if os.environ.has_key(_ENVIRON_DOMAIN):
                del os.environ[_ENVIRON_DOMAIN]
            return
        os.environ[_ENVIRON_EMAIL] = client_login_info['email']
        os.environ[_ENVIRON_DOMAIN] = client_login_info['domain']

    def process_exception(self, request, exception):
        if isinstance(exception, LoginRequiredError):
            request.session.pop(settings.SESSION_LOGIN_INFO_KEY, None)
            return HttpResponseRedirect(
                create_login_url(request.get_full_path()))
        elif isinstance(exception, CaptchaChallenge):
            import pickle
            client_login_info = request.session.get(
                settings.SESSION_LOGIN_INFO_KEY, {})
            client_login_info['captcha_url'] = exception.captcha_url
            client_login_info['captcha_token'] = exception.captcha_token
            client_login_info['service'] = pickle.dumps(
                exception.service, pickle.HIGHEST_PROTOCOL)
            request.session[settings.SESSION_LOGIN_INFO_KEY] = client_login_info
            return HttpResponseRedirect(
                reverse('captcha') + '?%s' % urllib.urlencode({
                    settings.REDIRECT_FIELD_NAME: request.get_full_path(),
                }))
        elif isinstance(exception, SetupRequiredError):
            if not is_current_user_admin():
                return HttpResponseRedirect(reverse('setup_required'))
            else:
                user = get_current_user()
                return HttpResponseRedirect(
                    reverse('domain_setup', args=(user.domain().domain,)) +
                    '?fix')
        elif isinstance(exception, AppsForYourDomainException):
            request.session.pop(settings.SESSION_LOGIN_INFO_KEY, None)
            memcache.flush_all()


def create_login_url(dest_url=settings.LOGIN_REDIRECT_URL):
    return reverse('openid_get_domain') + '?%s' % urllib.urlencode({
        settings.REDIRECT_FIELD_NAME: dest_url})


def create_logout_url(dest_url):
    return reverse('openid_logout') + '?%s' % urllib.urlencode({
        settings.REDIRECT_FIELD_NAME: dest_url})


def get_current_user():
    if os.environ.get(_ENVIRON_EMAIL) and os.environ.get(_ENVIRON_DOMAIN):
        return User(
            os.environ[_ENVIRON_EMAIL],
            os.environ[_ENVIRON_DOMAIN])
    else:
        return None


def get_current_domain():
    if os.environ.get(_ENVIRON_EMAIL) and os.environ.get(_ENVIRON_DOMAIN):
        return AppsDomain.get_by_key_name(os.environ[_ENVIRON_DOMAIN])


def is_current_user_admin():
    user = get_current_user()
    if user is None:
        return False
    return user.is_admin()


def _set_current_user(email, domain):
    os.environ[_ENVIRON_EMAIL] = email
    os.environ[_ENVIRON_DOMAIN] = domain

