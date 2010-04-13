from django import forms

from crgappspanel import models
from crgappspanel.consts import EMAIL_RELS, PHONE_RELS
from crgappspanel.helpers import fields, widgets
from django.utils.translation import ugettext as _

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
        data = self.cleaned_data
        
        password = data['password']
        if not password or password[0] == '' or password[0] != password[1]:
            return None
        
        return models.GAUser(
            user_name=data['user_name'],
            password=password,
            given_name=data['full_name'][0],
            family_name=data['full_name'][1])
    
    def populate(self, user):
        data = self.cleaned_data
        
        user.user_name = data['user_name']
        password = data['password']
        if password and password[0] != '' and password[0] == password[1]:
            user.password = password[0]
        user.change_password = data['change_password']
        user.given_name = data['full_name'][0]
        user.family_name = data['full_name'][1]
        user.admin = data['admin']
    
    def get_nickname(self):
        return self.cleaned_data['nicknames']


emails_c = '%(link_start)sAdd email%(link_end)s'
emails_e = 'Enter email:<br/>%(widget)s %(link_start)sCancel%(link_end)s'
phone_numbers_c = '%(link_start)sAdd phone number%(link_end)s'
phone_numbers_e = 'Enter phone number:<br/>%(widget)s %(link_start)sCancel%(link_end)s'


class SharedContactForm(forms.Form):
    full_name = forms.CharField(label='Name')
    real_name = fields.RealNameField(label='Real name')
    notes = forms.CharField(label='Notes', required=False,
        widget=forms.Textarea(attrs=dict(rows=5, cols=40)))
    company = forms.CharField(label='Company', required=False)
    role = forms.CharField(label='Role', required=False)
    
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
        data = self.cleaned_data
        
        name = models.Name(
            full_name=data['full_name'], name_prefix=data['real_name'][0],
            given_name=data['real_name'][1], family_name=data['real_name'][2])
        
        email = data['email']
        emails = [self._email(email)] if email else []
        
        phone_number = data['phone_number']
        phone_numbers = [self._phone_number(phone_number)] if phone_number else []
        
        company = self._ext_prop('company', data['company']) if data['company'] else None
        role = self._ext_prop('role', data['role']) if data['role'] else None
        
        return models.SharedContact(
            name=name, notes=data['notes'],
            emails=emails, phone_numbers=phone_numbers,
            extended_properties=[x for x in (company, role) if x is not None])
    
    def populate(self, shared_contact):
        data = self.cleaned_data
        
        email = data['emails']
        phone_number = data['phone_numbers']
        
        shared_contact.name.full_name = data['full_name']
        shared_contact.name.name_prefix = data['real_name'][0]
        shared_contact.name.given_name = data['real_name'][1]
        shared_contact.name.family_name = data['real_name'][2]
        shared_contact.notes = data['notes']
        
        return {
            'emails': [self._email(email)] if email else [],
            'phone_numbers': [self._phone_number(phone_number)] if phone_number else [],
            'company_str': data['company'],
            'role_str': data['role'],
        }
    
    def _email(self, email):
        return models.Email(address=email, rel=EMAIL_RELS[0])
    
    def _phone_number(self, phone_number):
        return models.PhoneNumber(number=phone_number, rel=PHONE_RELS[0])
    
    def _ext_prop(self, name, value):
        return models.ExtendedProperty(name=name, value=value)
    
    def clean(self):
        data = self.cleaned_data
        company = data['company']
        role = data['role']
        
        if not company and role:
            msg = _(u'Company is required if role is not empty.')
            self._errors['company'] = forms.util.ErrorList([msg])
            
            del data['company']
            del data['role']
        
        return data
