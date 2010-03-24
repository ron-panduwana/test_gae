import logging
from django import forms


class UserForm(forms.Form):
    user_name = forms.CharField(widget=forms.TextInput(attrs={'disabled': 'disabled'}))
    given_name = forms.CharField(label='Given name')
    family_name = forms.CharField(label='Family name')
    admin = forms.BooleanField(label='Privileges', required=False, help_text='Administrators can manage all users and settings for this domain')


class LoginForm(forms.Form):
    user_name = forms.CharField(required=True)
    password = forms.CharField(required=True, widget=forms.PasswordInput)
    captcha_token = forms.CharField(required=False, widget=forms.HiddenInput)
    captcha = forms.CharField(required=False)

    def __init__(self, *args, **kwargs):
        self.captcha_url = None
        super(LoginForm, self).__init__(*args, **kwargs)

    def clean_captcha(self):
        captcha = self.cleaned_data['captcha']
        if self.cleaned_data['captcha_token'] and not captcha:
            raise forms.ValidationError('You have to type captcha')
        return captcha

    def clean(self):
        if self._errors:
            return self.cleaned_data

        from google.appengine.api import memcache
        from gdata.apps.service import AppsService
        from gdata.service import CaptchaRequired, BadAuthentication
        from settings import APPS_DOMAIN

        service = AppsService(
            email='%s@%s' % (self.cleaned_data['user_name'], APPS_DOMAIN),
            password=self.cleaned_data['password'],
            domain=APPS_DOMAIN)

        try:
            service.ProgrammaticLogin(
                self.cleaned_data['captcha_token'] or None,
                self.cleaned_data['captcha'] or None)
        except CaptchaRequired:
            self.captcha_url = service.captcha_url
            self.data = self.data.copy()
            self.data['captcha_token'] = service.captcha_token
            raise forms.ValidationError('Please provide captcha')
        except BadAuthentication:
            raise forms.ValidationError('Invalid login data')

        self.token = service.GetClientLoginToken()

        return self.cleaned_data

