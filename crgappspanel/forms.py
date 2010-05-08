from django import forms
from django.forms.util import ErrorList
from django.utils.translation import ugettext as _

from crgappspanel import consts, models
from crgappspanel.consts import EMAIL_RELS, PHONE_RELS
from crgappspanel.helpers import fields, widgets

__all__ = ('UserForm', 'UserEmailSettingsForm', 'UserEmailFiltersForm',
    'SharedContactForm')


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


################################################################################
#                                    USERS                                     #
################################################################################


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

LANGUAGE_CHOICES = [('', u'Don\'t change')]
LANGUAGE_CHOICES.extend(consts.LANGUAGES)

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
    language = forms.ChoiceField(label='Language',
        choices=LANGUAGE_CHOICES, required=False)
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


HAS_ATTACHMENT_CHOICES = (
    ('', u'Doesn\'t matter'),
    ('e', u'Must have'),
)


class UserEmailFiltersForm(forms.Form):
    from_ = forms.EmailField(label='From', required=False)
    to = forms.EmailField(label='To', required=False)
    subject = forms.CharField(label='Subject', required=False)
    has_the_word = forms.CharField(label='Has the words', required=False)
    does_not_have_the_word = forms.CharField(label='Doesn\'t have', required=False)
    has_attachment = forms.ChoiceField(label='Has attachment',
        choices=HAS_ATTACHMENT_CHOICES, required=False)
    label = forms.CharField(label='Apply label', required=False)
    should_mark_as_read = forms.BooleanField(label='Mark as read', required=False)
    should_archive = forms.BooleanField(label='Archive', required=False)
    
    def clean_subject(self):
        return self.verify_illegal_chars('subject')
    
    def clean_has_the_word(self):
        return self.verify_illegal_chars('has_the_word')
    
    def clean_does_not_have_the_word(self):
        return self.verify_illegal_chars('does_not_have_the_word')
    
    def clean(self):
        data = self.cleaned_data
        filter_fields = ('from_', 'to', 'subject', 'has_the_word',
            'does_not_have_the_word', 'has_attachment')
        action_fields = ('label', 'should_mark_as_read', 'should_archive')
        
        if not any(data.get(key) for key in filter_fields):
            msg = _(u'At least one of fields: from, to, subject, has words, '
                'doesn\'t have, has attachment must be filled.')
            raise forms.ValidationError(msg)
        
        if not any(data.get(key) for key in action_fields):
            msg = _(u'At least one of fields apply label, mark as read, '
                'archive must be filled.')
            raise forms.ValidationError(msg)
        
        return data
    
    def verify_illegal_chars(self, key):
        illegal_chars = '[]()$&*'
        value = self.cleaned_data[key]
        if any(c in value for c in illegal_chars):
            msg = _(u'Characters %(illegal_chars)s are all illegal.') % dict(illegal_chars=illegal_chars)
            raise forms.ValidationError(msg)
        return value


reply_to_c = 'Set %(link_start)sanother%(link_end)s reply to address'
reply_to_e = '%(widget)s %(link_start)sCancel%(link_end)s'


class UserEmailAliasesForm(forms.Form):
    name = forms.CharField(label='Name')
    address = forms.EmailField(label='Email address')
    reply_to = forms.EmailField(label='Reply to', required=False,
        widget=widgets.SwapWidget(reply_to_c, forms.TextInput(), reply_to_e))
    make_default = forms.BooleanField(label='Make default', required=False)


################################################################################
#                                    GROUPS                                    #
################################################################################


class GroupForm(forms.Form):
    id = forms.CharField(label='Identifier')
    name = forms.CharField(label='Name')
    email_permission = forms.ChoiceField(label='Email permission',
        choices=consts.GROUP_EMAIL_PERMISSION_CHOICES)
    description = forms.CharField(label='Description', required=False,
        widget=forms.Textarea(attrs=dict(rows=3, cols=30)))
    
    def create(self):
        data = self.cleaned_data
        
        return models.GAGroup(
            id=data['id'],
            name=data['name'],
            email_permission=data['email_permission'],
            description='')
    
    def populate(self, group):
        data = self.cleaned_data
        
        group.name = data['name']
        group.email_permission = data['email_permission']
        group.description = data['description']
        
        return data['id']


owner_c = '%(link_start)sAdd%(link_end)s another owner'
owner_e = '%(widget)s %(link_start)sCancel%(link_end)s'
member_c = '%(link_start)sAdd%(link_end)s another member'
member_e = '%(widget)s %(link_start)sCancel%(link_end)s'


class GroupMembersForm(forms.Form):
    owner = forms.EmailField(label='Owner', required=False,
        widget=widgets.SwapWidget(owner_c, forms.TextInput(), owner_e))
    member = forms.EmailField(label='Members', required=False,
        widget=widgets.SwapWidget(member_c, forms.TextInput(), member_e))


################################################################################
#                               SHARED CONTACTS                                #
################################################################################


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
        company = data.get('company')
        role = data.get('role')
        
        # role filled => company must be filled
        if not company and role:
            msg = _(u'Company is required if role is not empty.')
            self._errors['company'] = forms.ErrorList([msg])
            
            data.pop('company', None)
            data.pop('role', None)
        
        return data
