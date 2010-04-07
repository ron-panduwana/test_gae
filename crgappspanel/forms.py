from django import forms

from crgappspanel import models
from crgappspanel.helpers import fields, widgets

__all__ = ('UserForm')

password_c = '%(widget)s%(link_start)sChange password%(link_end)s WARNING: dangerous, without confirmation yet!'
password_1 = widgets.DoubleWidget(forms.HiddenInput(), forms.HiddenInput())
password_e = 'Enter new password:<br/>%(widget)s %(link_start)sCancel%(link_end)s'
password_2 = widgets.DoubleWidget(forms.PasswordInput(), forms.PasswordInput())

nicknames_c = '%(widget)s%(link_start)sAdd nickname%(link_end)s'
nicknames_e = 'Enter nickname:<br/>%(widget)s %(link_start)sCancel%(link_end)s'


class UserForm(forms.Form):
    user_name = forms.CharField(label='Username')
    password = fields.CharField2(label='Password', required=False, widget=password_2)
    change_password = forms.BooleanField(label='Password', required=False,
        help_text='Require a change of password in the next sign in')
    full_name = fields.CharField2(label='Full name')
    admin = forms.BooleanField(label='Privileges', required=False,
        help_text='Administrators can manage all users and settings for this domain')
    nicknames = forms.CharField(label='Nicknames', required=False,
        widget=widgets.SwapWidget(forms.HiddenInput(), nicknames_c, forms.TextInput(), nicknames_e))
    
    def create(self):
        password = self.cleaned_data['password']
        if not password or password[0] == '' or password[0] != password[1]:
            return None
        
        return models.GAUser(
            user_name=self.cleaned_data['user_name'],
            password=password,
            given_name=self.cleaned_data['full_name'][0],
            family_name=self.cleaned_data['full_name'][1])
    
    def populate(self, user):
        user.user_name = self.cleaned_data['user_name']
        password = self.cleaned_data['password']
        if password and password[0] != '' and password[0] == password[1]:
            user.password = password[0]
        user.change_password = self.cleaned_data['change_password']
        user.given_name = self.cleaned_data['full_name'][0]
        user.family_name = self.cleaned_data['full_name'][1]
        user.admin = self.cleaned_data['admin']
    
    def get_nickname(self):
        nicknames = self.cleaned_data['nicknames'].strip()
        if nicknames:
            return nicknames
        return None


emails_c = '%(widget)s%(link_start)sAdd email%(link_end)s'
emails_e = 'Enter email:<br/>%(widget)s %(link_start)sCancel%(link_end)s'


class SharedContactForm(forms.Form):
    name = forms.CharField(label='Name')
    notes = forms.CharField(label='Notes')
    email = forms.CharField(label='Email')
    emails = forms.CharField(label='Emails', required=False,
        widget=widgets.SwapWidget(forms.HiddenInput(), emails_c, forms.TextInput(), emails_e))
    
    def create(self):
        email = models.ContactEmail(
            address=self.cleaned_data['email'],
            primary=True)
        return models.SharedContact(
            name=self.cleaned_data['name'],
            notes=self.cleaned_data['notes'],
            emails=[email])
    
    def populate(self, shared_contact):
        email = self.cleaned_data['emails'].strip()
        
        shared_contact.name = self.cleaned_data['name']
        shared_contact.notes = self.cleaned_data['notes']
        return [email] if email else []
