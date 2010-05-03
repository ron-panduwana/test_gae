from django import forms
from django.forms.util import ErrorList

from crgappspanel import models
from crgappspanel.consts import EMAIL_RELS, PHONE_RELS
from crgappspanel.helpers import fields, widgets
from django.utils.translation import ugettext as _

__all__ = ('UserForm', 'UserEmailSettingsForm', 'SharedContactForm')


ENABLE = 'e'
DISABLE = 'd'
ENABLE_DISABLE = (ENABLE, DISABLE)


def create_on_off_keep(on_text, off_text):
    return (
        ('', u'Don\'t change'),
        ('e', on_text),
        ('d', off_text),
    )

def create_exact_keep(*values):
    ret = [('', u'Don\'t change')]
    ret.extend((v, v) for v in values)
    return ret


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


ENABLE_DISABLE_KEEP = create_on_off_keep(u'Enable', u'Disable')

FORWARD_CHOICES = (
    ('', u'Don\'t change'),
    ('ek', u'Forward and keep'),
    ('ea', u'Forward and archive'),
    ('ed', u'Forward and delete'),
    ('d', u'Don\'t forward'),
)
FORWARD_ENABLES = ('ek', 'ea', 'ed')
FORWARD_DISABLES = ('d')

POP3_CHOICES = (
    ('', u'Don\'t change'),
    ('ea', u'Enable for all emails'),
    ('en', u'Enable for emails for now on'),
    ('d', u'Disable'),
)
POP3_ENABLES = ('ea', 'en')
POP3_DISABLES = ('d')

MESSAGES_PER_PAGE_CHOICES = create_exact_keep(u'25', u'50', u'100')
UNICODE_CHOICES = create_on_off_keep(u'Use Unicode (UTF-8)', u'Use default text encoding')

#forward_c = '%(link_start)sEnable forwarding%(link_end)s'
#forward_e = 'Forward to: %(widget)s %(link_start)sCancel%(link_end)s'


class UserEmailSettingsForm(forms.Form):
    forward = forms.ChoiceField(label='Forwarding',
        choices=FORWARD_CHOICES, required=False)
    forward_to = forms.EmailField(label='Forward to', required=False)
    pop3 = forms.ChoiceField(label='POP3',
        choices=POP3_CHOICES, required=False)
    imap = forms.ChoiceField(label='IMAP',
        choices=ENABLE_DISABLE_KEEP, required=False)
    messages_per_page = forms.ChoiceField(label='Messages per page',
        choices=MESSAGES_PER_PAGE_CHOICES, required=False)
    web_clips = forms.ChoiceField(label='Web Clips',
        choices=ENABLE_DISABLE_KEEP, required=False)
    snippets = forms.ChoiceField(label='Snippets',
        choices=ENABLE_DISABLE_KEEP, required=False)
    shortcuts = forms.ChoiceField(label='Keyboard shortcuts',
        choices=ENABLE_DISABLE_KEEP, required=False)
    arrows = forms.ChoiceField(label='Personal level indicators',
        choices=ENABLE_DISABLE_KEEP, required=False)
    unicode = forms.ChoiceField(label='Outgoing mail encoding',
        choices=UNICODE_CHOICES, required=False)
    signature = forms.ChoiceField(label='Signature',
        choices=ENABLE_DISABLE_KEEP, required=False)
    signature_new = forms.CharField(label='', required=False,
        widget=forms.Textarea(attrs=dict(rows=3, cols=30)))
    
    def get_boolean(self, key):
        value = self.cleaned_data[key]
        if value in ENABLE_DISABLE:
            return value == ENABLE
        return None
    
    def clean(self):
        data = self.cleaned_data
        forward = data.get('forward')
        forward_to = data.get('forward_to')
        signature = data.get('signature')
        signature_new = data.get('signature_new')
        
        # enabling forwarding => forward_to must be filled
        if forward in FORWARD_ENABLES and not forward_to:
            msg = _(u'Forwarding address must be specified when enabling forwarding.')
            self._errors['forward_to'] = ErrorList([msg])
            
            data.pop('forward', None)
            data.pop('forward_to', None)
        
        # not enabling forwarding => forward_to must be empty
        if forward not in FORWARD_ENABLES and forward_to:
            msg = _(u'Forwarding address must not be specified when not enabling forwarding.')
            self._errors['forward_to'] = ErrorList([msg])
            
            data.pop('forward', None)
            data.pop('forward_to', None)
        
        # enabling signature => signature_new must be filled
        if signature == ENABLE and not signature_new:
            msg = _(u'Signature must be specified when enabling signature.')
            self._errors['signature_new'] = ErrorList([msg])
            
            data.pop('signature')
            data.pop('signature_new')
        
        # not enabling signature => signature_new must be empty
        if signature != ENABLE and signature_new:
            msg = _(u'Signature must not be specified when not enabling signature.')
            self._errors['signature_new'] = ErrorList([msg])
            
            data.pop('signature')
            data.pop('signature_new')
        
        return data


emails_c = '%(link_start)sAdd email%(link_end)s'
emails_e = 'Enter email:<br/>%(widget)s %(link_start)sCancel%(link_end)s'
phone_numbers_c = '%(link_start)sAdd phone number%(link_end)s'
phone_numbers_e = 'Enter phone number:<br/>%(widget)s %(link_start)sCancel%(link_end)s'


class SharedContactForm(forms.Form):
    full_name = forms.CharField(label='Name')
    real_name = fields.RealNameField(label='Real name', required=False)
    notes = forms.CharField(label='Notes', required=False,
        widget=forms.Textarea(attrs=dict(rows=3, cols=30)))
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
        company = data.get('company', None)
        role = data.get('role', None)
        
        # role filled => company must be filled
        if not company and role:
            msg = _(u'Company is required if role is not empty.')
            self._errors['company'] = forms.ErrorList([msg])
            
            data.pop('company', None)
            data.pop('role', None)
        
        return data
