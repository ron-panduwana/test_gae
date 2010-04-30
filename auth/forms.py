import logging
from django import forms
from django.utils.translation import ugettext_lazy as _
from gdata.apps import service
from gdata.service import CaptchaRequired, BadAuthentication


class CaptchaForm(forms.Form):
    captcha_token = forms.CharField(required=False, widget=forms.HiddenInput)
    captcha_url = forms.CharField(required=False, widget=forms.HiddenInput)
    captcha_service = forms.CharField(widget=forms.HiddenInput, initial='apps')
    captcha = forms.CharField(required=False)
    is_old_api = forms.BooleanField(
        required=False, initial=True, widget=forms.HiddenInput)

    def clean_captcha(self):
        captcha = self.cleaned_data['captcha']
        if self.cleaned_data['captcha_token'] and not captcha:
            raise forms.ValidationError(_('You have to type captcha'))
        return captcha


class DomainSetupForm(CaptchaForm):
    account = forms.CharField(label=_('Administrator account'))
    password = forms.CharField(
        label=_('Administrator password'),
        required=True, widget=forms.PasswordInput)
    domain = forms.CharField(widget=forms.HiddenInput, required=True)
    callback = forms.URLField(required=False, widget=forms.HiddenInput)

    def clean(self):
        if self._errors:
            return self.cleaned_data

        account = self.cleaned_data['account']
        domain = self.cleaned_data['domain']
        password = self.cleaned_data['password']
        email = '%s@%s' % (account, domain)
        apps_service = service.AppsService(
            email=email, domain=domain, password=password)
        try:
            apps_service.ProgrammaticLogin(
                self.cleaned_data['captcha_token'] or None,
                self.cleaned_data['captcha'] or None)
        except CaptchaRequired:
            self.data = self.data.copy()
            self.data['captcha_token'] = apps_service.captcha_token
            self.data['captcha_url'] = apps_service.captcha_url
            raise forms.ValidationError(_('Please provide CAPTCHA'))
        except BadAuthentication:
            logging.exception('DomainSetupForm')
            raise forms.ValidationError(
                _('Please provide correct authentication credentials'))
        return self.cleaned_data

