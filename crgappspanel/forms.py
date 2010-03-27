from django import forms

from crgappspanel import models
from crgappspanel.helpers import fields, widgets

__all__ = ('UserForm', 'LoginForm')

_password_c = '%(widget)s%(link_start)sChange password%(link_end)s WARNING: dangerous, without confirmation yet!'
_password_e = 'Enter new password:<br/>%(widget)s %(link_start)sCancel%(link_end)s'
_nicknames_c = '%(widget)s%(link_start)sAdd nickname%(link_end)s'
_nicknames_e = 'Enter nickname:<br/>%(widget)s %(link_start)sCancel%(link_end)s'

class UserForm(forms.Form):
    user_name = forms.CharField(label='User name')
    password = forms.CharField(label='Password', required=False,
        widget=widgets.SwapWidget(forms.HiddenInput(), _password_c, forms.PasswordInput(), _password_e))
    change_password = forms.BooleanField(label='Password', required=False,
        help_text='Require a change of password in the next sign in')
    full_name = fields.CharField2(label='Full name')
    admin = forms.BooleanField(label='Privileges', required=False,
        help_text='Administrators can manage all users and settings for this domain')
    nicknames = forms.CharField(label='Nicknames', required=False,
        widget=widgets.SwapWidget(forms.HiddenInput(), _nicknames_c, forms.TextInput(), _nicknames_e))
    
    def populate(self, user):
        user.user_name = self.cleaned_data['user_name']
        user.password = self.cleaned_data['password']
        user.change_password = self.cleaned_data['change_password']
        user.given_name = self.cleaned_data['full_name'][0]
        user.family_name = self.cleaned_data['full_name'][1]
        user.admin = self.cleaned_data['admin']
    
    def get_nickname(self):
        nicknames = self.cleaned_data['nicknames'].strip()
        if nicknames:
            return nicknames
        return None

