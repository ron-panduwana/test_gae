from django import forms

from crgappspanel import models
from crgappspanel.helpers import fields, widgets

__all__ = ('UserForm', 'LoginForm')

password_c = '%(widget)s%(link_start)sChange password%(link_end)s WARNING: dangerous, without confirmation yet!'
password_1 = widgets.DoubleWidget(forms.HiddenInput(), forms.HiddenInput())
password_e = 'Enter new password:<br/>%(widget)s %(link_start)sCancel%(link_end)s'
password_2 = widgets.DoubleWidget(forms.PasswordInput(), forms.PasswordInput())

nicknames_c = '%(widget)s%(link_start)sAdd nickname%(link_end)s'
nicknames_e = 'Enter nickname:<br/>%(widget)s %(link_start)sCancel%(link_end)s'


class UserForm(forms.Form):
    user_name = forms.CharField(label='User name')
    password = fields.CharField2(label='Password', required=False, widget=password_2)
    change_password = forms.BooleanField(label='Password', required=False,
        help_text='Require a change of password in the next sign in')
    full_name = fields.CharField2(label='Full name')
    admin = forms.BooleanField(label='Privileges', required=False,
        help_text='Administrators can manage all users and settings for this domain')
    nicknames = forms.CharField(label='Nicknames', required=False,
        widget=widgets.SwapWidget(forms.HiddenInput(), nicknames_c, forms.TextInput(), nicknames_e))
    
    def populate(self, user):
        #for key in ['user_name', 'password', 'password_0', 'full_name']:
        #    if key in self.cleaned_data:
        #        print key, '=', self._cd(key)
        user.user_name = self._cd('user_name')
        if self._cd('password')[0] != '' and self._cd('password')[0] == self._cd('password')[1]:
            user.password = self._cd('password')[0]
        user.change_password = self._cd('change_password')
        user.given_name = self._cd('full_name')[0]
        user.family_name = self._cd('full_name')[1]
        user.admin = self._cd('admin')
    
    def _cd(self, attr):
        return self.cleaned_data[attr]
    
    def get_nickname(self):
        nicknames = self.cleaned_data['nicknames'].strip()
        if nicknames:
            return nicknames
        return None

