from django import forms

from crgappspanel import models
from crgappspanel.consts import EMAIL_RELS, PHONE_RELS
from crgappspanel.helpers import fields, widgets

__all__ = ('UserForm')

password_c = '%(widget)s%(link_start)sChange password%(link_end)s WARNING: dangerous, without confirmation yet!'
password_1 = widgets.DoubleWidget(forms.HiddenInput(), forms.HiddenInput())
password_e = 'Enter new password:<br/>%(widget)s %(link_start)sCancel%(link_end)s'
password_2 = widgets.DoubleWidget(forms.PasswordInput(), forms.PasswordInput())

nicknames_c = '%(link_start)sAdd nickname%(link_end)s'
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
        widget=widgets.SwapWidget(nicknames_c, forms.TextInput(), nicknames_e))
    
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


emails_c = '%(link_start)sAdd email%(link_end)s'
emails_e = 'Enter email:<br/>%(widget)s %(link_start)sCancel%(link_end)s'
phone_numbers_c = '%(link_start)sAdd phone number%(link_end)s'
phone_numbers_e = 'Enter phone number:<br/>%(widget)s %(link_start)sCancel%(link_end)s'


class SharedContactForm(forms.Form):
    full_name = forms.CharField(label='Name')
    real_name = fields.RealNameField(label='Real name')
    notes = forms.CharField(label='Notes', required=False,
        widget=forms.Textarea(attrs=dict(rows=5, cols=40)))
    
    # email field to show when creating contact
    email = forms.CharField(label='Email', required=False)
    # emails filed to show when editing contact
    emails = forms.CharField(label='Emails', required=False,
        widget=widgets.SwapWidget(emails_c, forms.TextInput(), emails_e))
    
    # phone number field to show when creating contact
    phone_number = forms.CharField(label='Phone number', required=False)
    # phone numbers field to show when editing contact
    phone_numbers = forms.CharField(label='Phone numbers', required=False,
        widget=widgets.SwapWidget(phone_numbers_c, forms.TextInput(), phone_numbers_e))
    
    def create(self):
        name = models.Name(
            full_name=self.cleaned_data['full_name'],
            name_prefix=self.cleaned_data['real_name'][0],
            given_name=self.cleaned_data['real_name'][1],
            family_name=self.cleaned_data['real_name'][2])
        
        email = self.cleaned_data['email'].strip()
        if email:
            emails = [
                models.Email(
                    address=email,
                    rel=EMAIL_RELS[0])
            ]
        else:
            emails = []
        
        phone_number = self.cleaned_data['phone_number'].strip()
        if phone_number:
            phone_numbers = [
                models.PhoneNumber(
                    number=phone_number,
                    rel=PHONE_RELS[0])
            ]
        else:
            phone_numbers = []
        
        return models.SharedContact(
            name=name,
            notes=self.cleaned_data['notes'],
            emails=emails,
            phone_numbers=phone_numbers)
    
    def populate(self, shared_contact):
        email = self.cleaned_data['emails'].strip()
        phone_number = self.cleaned_data['phone_numbers'].strip()
        
        shared_contact.name.full_name = self.cleaned_data['full_name']
        shared_contact.name.name_prefix = self.cleaned_data['real_name'][0]
        shared_contact.name.given_name = self.cleaned_data['real_name'][1]
        shared_contact.name.family_name = self.cleaned_data['real_name'][2]
        shared_contact.notes = self.cleaned_data['notes']
        return {
            'emails': [self._email(email)] if email else [],
            'phone_numbers': [self._phone_number(phone_number)] if phone_number else [],
        }
    
    def _email(self, email):
        return models.Email(
            address=email,
            rel=EMAIL_RELS[0])
    
    def _phone_number(self, phone_number):
        return models.PhoneNumber(
            number=phone_number,
            rel=PHONE_RELS[0])
