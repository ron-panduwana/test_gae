import logging
import re
from google.appengine.api import memcache
from django import forms
from django.utils.translation import ugettext_lazy as _
from gdata.apps import service
from gdata.service import CaptchaRequired, BadAuthentication
from crauth.users import SetupRequiredError, _SERVICE_MEMCACHE_TOKEN_KEY
from crauth.models import AppsDomain
from crlib import forms as crforms


RE_DOMAIN = re.compile(r'^(?:[-\w]+\.)+[a-z]{2,6}$')
# Look at http://www.google.com/support/a/bin/answer.py?answer=33386 for
# description of allowed characters in usernames and passwords
RE_USERNAME = re.compile(r'^[a-z0-9\-_\.\']+$')


class VerbatimWidget(forms.Widget):
    def render(self, name, value, attrs=None):
        return value or ''


class DomainNameForm(forms.Form):
    domain = forms.RegexField(
        required=True, regex=RE_DOMAIN, label='www.',
        error_messages={'invalid': _('Please enter valid domain name')})


class ChooseDomainForm(forms.Form):
    def __init__(self, *args, **kwargs):
        choices = kwargs.pop('choices', set())
        super(ChooseDomainForm, self).__init__(*args, **kwargs)
        self.fields['domain'] = crforms.ChoiceWithOtherField(
            required=True, choices=choices,
            label=_('Please select Google apps domain you want to log in to:'))

    def clean_domain(self):
        main, other = self.cleaned_data['domain']
        if main == 'other':
            if not RE_DOMAIN.match(other):
                raise forms.ValidationError('Please enter valid domain name')
            return other
        return main


class CaptchaForm(forms.Form):
    captcha_token = forms.CharField(required=False, widget=forms.HiddenInput)
    captcha_url = forms.CharField(required=False, widget=VerbatimWidget)
    captcha = forms.CharField(required=False)

    def __init__(self, user=None, service=None, *args, **kwargs):
        self.user = user
        self.service = service
        super(CaptchaForm, self).__init__(*args, **kwargs)

    def clean_captcha(self):
        captcha = self.cleaned_data['captcha']
        if self.cleaned_data['captcha_token'] and not captcha:
            raise forms.ValidationError(_('You have to type captcha'))
        return captcha

    def clean(self):
        from gdata.client import CaptchaChallenge
        if self._errors:
            return self.cleaned_data
        try:
            self.user.client_login(
                self.service, self.cleaned_data['captcha_token'],
                self.cleaned_data['captcha'])
        except CaptchaChallenge, challenge:
            self.data = self.data.copy()
            self.data['captcha_token'] = challenge.captcha_token
            self.data['captcha_url'] = challenge.captcha_url
            self.data['captcha'] = ''
            raise forms.ValidationError(_('Please enter the CAPTCHA'))
        return self.cleaned_data


class DomainSetupForm(CaptchaForm):
    account = forms.RegexField(
        regex=RE_USERNAME, label=_('Administrator account'),
        error_messages={'invalid': _(
            'Usernames may contain letters (a-z), numbers (0-9), dashes (-), '
            'underscores (_), periods (.), and apostrophes (\'), and may not '
            'contain an equal sign (=) or brackets (<,>).')})
    password = forms.CharField(
        label=_('Administrator password'),
        required=True, widget=forms.PasswordInput, min_length=6)
    domain = forms.CharField(widget=forms.HiddenInput, required=True)
    callback = forms.URLField(required=False, widget=forms.HiddenInput)

    def clean(self):
        if self._errors:
            return self.cleaned_data

        account = self.cleaned_data['account']
        domain = self.cleaned_data['domain']
        password = self.cleaned_data['password']
        email = '%s@%s' % (account, domain)

        apps_domain = AppsDomain.get_by_key_name(domain)
        if not apps_domain:
            old_credentials = {}
            apps_domain = AppsDomain(
                key_name=domain,
                domain=domain)
        else:
            old_credentials = {
                'email': apps_domain.admin_email,
                'password': apps_domain.admin_password,
            }

        def restore_credentials():
            if old_credentials:
                apps_domain.admin_email = old_credentials['email']
                apps_domain.admin_password = old_credentials['password']
                apps_domain.put()

        memcache.delete(_SERVICE_MEMCACHE_TOKEN_KEY % (
            domain, self.service.service))
        apps_domain.admin_email = email
        apps_domain.admin_password = password
        apps_domain.put()

        try:
            cleaned_data = super(DomainSetupForm, self).clean()
            self.service.RetrieveUser(account)
            return cleaned_data
        except service.AppsForYourDomainException:
            restore_credentials()
            raise forms.ValidationError(
                _('Make sure to provide credentials for administrator of your '
                  'domain'))
        except SetupRequiredError:
            restore_credentials()
            raise forms.ValidationError(
                _('Please provide correct authentication credentials'))

