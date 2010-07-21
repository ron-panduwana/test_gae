from django import forms
from django.forms.util import ErrorList
from django.utils.translation import ugettext as _

import crauth
from crauth.models import Role
from crgappspanel import consts, models
from crgappspanel.consts import EMAIL_RELS, PHONE_RELS
from crgappspanel.helpers import fields, widgets
from crlib import regexps

__all__ = ('UserForm', 'UserEmailSettingsForm', 'UserEmailFiltersForm',
    'SharedContactForm', 'CalendarResourceForm')


ENABLE = 'e'
DISABLE = 'd'
ENABLE_DISABLE = (ENABLE, DISABLE)


def create_on_off_keep(on_text, off_text):
    return (
        ('', _('Don\'t change')),
        ('e', _(on_text)),
        ('d', _(off_text)),
    )

def create_exact_keep(*values):
    ret = [('', _('Don\'t change'))]
    ret.extend((v, v) for v in values)
    return ret


class Form(forms.Form):
    def add_error(self, field, msg):
        if self._errors.has_key(field):
            self._errors[field].append(msg)
        else:
            self._errors[field] = ErrorList([msg])


################################################################################
#                           GENERAL VALIDATION CODE                            #
################################################################################


lower_start = ord('a')
lower_end = ord('z')
upper_start = ord('A')
upper_end = ord('Z')
digit_start = ord('0')
digit_end = ord('9')


def enforce_valid(value, lower=False, upper=False, digits=False, other=''):
    """Enforces that all characters in value are valid characters.
    Valid characters are:
    1. All characters in other argument
    2. Lowercase english letters if lower argument evaluates to True
    3. Uppercase english letters if upper argument evaluates to True
    4. Digits is digits argument evaluates to True
    Returns value if passed, throws ValidationError otherwise.
    """
    
    if not value:
        return value
    
    for c in value:
        x = ord(c)
        if c in other:
            pass
        elif lower_start <= x <= lower_end:
            if not lower:
                msg = _('Lowercase english letters are not allowed.')
                raise forms.ValidationError(msg)
        elif upper_start <= x <= upper_end:
            if not upper:
                msg = _('Uppercase english letters are not allowed.')
                raise forms.ValidationError(msg)
        elif digit_start <= x <= digit_end:
            if not digits:
                msg = _('Digits are not allowed.')
                raise forms.ValidationError(msg)
        else:
            msg = _('Character \'%(char)s\' is not allowed.') % dict(char=c)
            raise forms.ValidationError(msg)
    
    return value


def enforce_invalid(value, lower=False, upper=False, digits=False, other=''):
    """Enforces that no single character in value is invalid character.
    Invalid characters are:
    1. All characters in other argument
    2. Lowercase english letters if lower argument evaluates to True
    3. Uppercase english letters if upper argument evaluates to True
    4. Digits is digits argument evaluates to True
    Returns value if passed, throws ValidationError otherwise.
    """
    
    if not value:
        return value
    
    for c in value:
        x = ord(c)
        if c in other:
            msg = _('Character \'%(char)s\' is not allowed.') % dict(char=c)
            raise forms.ValidationError(msg)
        elif lower_start <= x <= lower_end:
            if lower:
                msg = _('Lowercase english letters are not allowed.')
                raise forms.ValidationError(msg)
        elif upper_start <= x <= upper_end:
            if upper:
                msg = _('Uppercase english letters are not allowed.')
                raise forms.ValidationError(msg)
        elif digit_start <= x <= digit_end:
            if digits:
                msg = _('Digits are not allowed.')
                raise forms.ValidationError(msg)
    
    return value


def enforce_some_alnum(value):
    """Enforces that at least one alphanumeric character exists in value.
    Returns value is passed, throws ValidationError otherwise.
    """
    
    if value:
        for c in value:
            x = ord(c)
            if lower_start <= x <= lower_end:
                return value
            elif upper_start <= x <= upper_end:
                return value
            elif digit_start <= x <= digit_end:
                return value
    
    msg = _('There must be at least one letter or digit.')
    raise forms.ValidationError(msg)


################################################################################
#                                    USERS                                     #
################################################################################


password_c = '%(widget)s%(link_start)sChange password%(link_end)s WARNING: dangerous, without confirmation yet!'
password_1 = widgets.DoubleWidget(forms.HiddenInput(), forms.HiddenInput())
password_e = 'Enter new password:<br/>%(widget)s %(link_start)sCancel%(link_end)s'
password_2 = widgets.DoubleWidget(forms.PasswordInput(), forms.PasswordInput())

nicknames_c = '%(link_start)sAdd nickname%(link_end)s'
nicknames_e = 'Enter nickname:<br/>%(widget)s %(link_start)sCancel%(link_end)s'


full_name_kwargs = {
    'regex': regexps.RE_FIRST_LAST_NAME,
    'error_messages': {'invalid': regexps.ERROR_FIRST_LAST_NAME},
}

class UserForm(Form):
    user_name = forms.RegexField(
        regex=regexps.RE_USERNAME, label=_('Username'),
        error_messages={'invalid': regexps.ERROR_USERNAME})
    password = fields.CharField2(label=_('Password'), required=False, widget=password_2)
    change_password = forms.BooleanField(label=_('Password'), required=False,
        help_text='Require a change of password in the next sign in')
    full_name = fields.RegexField2(
        label=_('Full name'), kwargs1=full_name_kwargs,
        kwargs2=full_name_kwargs)
    nicknames = forms.CharField(label=_('Nicknames'), required=False,
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
        if password and password[0] and password[0] == password[1]:
            user.password = password[0]
        user.change_password = data['change_password']
        user.given_name = data['full_name'][0]
        user.family_name = data['full_name'][1]
    
    def get_nickname(self):
        return self.cleaned_data['nicknames']
    
    def clean_full_name(self):
        data = self.cleaned_data['full_name']
        first_name = data[0].strip()
        family_name = data[1].strip()
        if first_name == '':
            raise forms.ValidationError(_('First name is required.'))
        if family_name == '':
            raise forms.ValidationError(_('Family name is required.'))
        return [first_name, family_name]
        
    def clean_nicknames(self):
        data = self.cleaned_data['nicknames']
        if data and not regexps.RE_USERNAME.match(data):
            raise forms.ValidationError(regexps.ERROR_NICKNAME)
        return data
    
    def clean_password(self):
        password = self.cleaned_data['password']
        if not password:
            return password
        pass_a, pass_b = password
        if pass_a != pass_b:
            raise forms.ValidationError(_('These passwords don\'t match.'))
        return [pass_a, pass_b]


roles_c = '%(link_start)sAdd role%(link_end)s'
roles_e = 'Choose role:<br/>%(widget)s %(link_start)sCancel%(link_end)s'


class UserRolesForm(forms.Form):
    roles = forms.CharField(label=_('Roles'), required=False,
        widget=widgets.SwapWidget(roles_c, forms.Select(), roles_e))
    
    def __init__(self, *args, **kwargs):
        if 'choices' in kwargs:
            choices = kwargs['choices']
            del kwargs['choices']
        else:
            choices = None
        
        super(UserRolesForm, self).__init__(*args, **kwargs)
        
        if choices:
            self.fields['roles'].widget.widget.choices = choices


ADD_AS_CHOICES = (('owner', _('Owner')), ('member', _('Member')))


class UserGroupsForm(forms.Form):
    groups = forms.MultipleChoiceField(label=_('Add to groups'), choices=(),
        widget=forms.SelectMultiple(attrs={'class':'long'}))
    add_as = forms.ChoiceField(label=_('Add as'), choices=ADD_AS_CHOICES)


ENABLE_DISABLE_KEEP = create_on_off_keep(_('Enable'), _('Disable'))

LANGUAGE_CHOICES = [('', _('Don\'t change'))]
LANGUAGE_CHOICES.extend(consts.LANGUAGES)

FORWARD_CHOICES = (
    ('', _('Don\'t change')),
    ('ek', _('Forward and keep')),
    ('ea', _('Forward and archive')),
    ('ed', _('Forward and delete')),
    ('d', _('Don\'t forward')),
)
FORWARD_ENABLES = ('ek', 'ea', 'ed')
FORWARD_DISABLES = ('d')

POP3_CHOICES = (
    ('', _('Don\'t change')),
    ('ea', _('Enable for all emails')),
    ('en', _('Enable for emails for now on')),
    ('d', _('Disable')),
)
POP3_ENABLES = ('ea', 'en')
POP3_DISABLES = ('d')

MESSAGES_PER_PAGE_CHOICES = create_exact_keep(u'25', u'50', u'100')
UNICODE_CHOICES = create_on_off_keep(_('Use Unicode (UTF-8)'), _('Use default text encoding'))

#forward_c = '%(link_start)sEnable forwarding%(link_end)s'
#forward_e = 'Forward to: %(widget)s %(link_start)sCancel%(link_end)s'


class UserEmailSettingsForm(forms.Form):
    language = forms.ChoiceField(label=_('Language'),
        choices=LANGUAGE_CHOICES, required=False)
    forward = forms.ChoiceField(label=_('Forwarding'),
        choices=FORWARD_CHOICES, required=False)
    forward_to = forms.EmailField(label=_('Forward to'), required=False,
        widget=forms.TextInput(attrs={'class':'long'}))
    pop3 = forms.ChoiceField(label=_('POP3'),
        choices=POP3_CHOICES, required=False)
    imap = forms.ChoiceField(label=_('IMAP'),
        choices=ENABLE_DISABLE_KEEP, required=False)
    messages_per_page = forms.ChoiceField(label=_('Messages per page'),
        choices=MESSAGES_PER_PAGE_CHOICES, required=False)
    web_clips = forms.ChoiceField(label=_('Web Clips'),
        choices=ENABLE_DISABLE_KEEP, required=False)
    snippets = forms.ChoiceField(label=_('Snippets'),
        choices=ENABLE_DISABLE_KEEP, required=False)
    shortcuts = forms.ChoiceField(label=_('Keyboard shortcuts'),
        choices=ENABLE_DISABLE_KEEP, required=False)
    arrows = forms.ChoiceField(label=_('Personal level indicators'),
        choices=ENABLE_DISABLE_KEEP, required=False)
    unicode = forms.ChoiceField(label=_('Outgoing mail encoding'),
        choices=UNICODE_CHOICES, required=False)
    signature = forms.ChoiceField(label=_('Signature'),
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
            msg = _('Forwarding address must be specified when enabling forwarding.')
            self._errors['forward_to'] = ErrorList([msg])
            
            data.pop('forward', None)
            data.pop('forward_to', None)
        
        # not enabling forwarding => forward_to must be empty
        if forward not in FORWARD_ENABLES and forward_to:
            msg = _('Forwarding address must not be specified when not enabling forwarding.')
            self._errors['forward_to'] = ErrorList([msg])
            
            data.pop('forward', None)
            data.pop('forward_to', None)
        
        # enabling signature => signature_new must be filled
        if signature == ENABLE and not signature_new:
            msg = _('Signature must be specified when enabling signature.')
            self._errors['signature_new'] = ErrorList([msg])
            
            data.pop('signature')
            data.pop('signature_new')
        
        # not enabling signature => signature_new must be empty
        if signature != ENABLE and signature_new:
            msg = _('Signature must not be specified when not enabling signature.')
            self._errors['signature_new'] = ErrorList([msg])
            
            data.pop('signature')
            data.pop('signature_new')
        
        return data


HAS_ATTACHMENT_CHOICES = (
    ('', _('Doesn\'t matter')),
    ('e', _('Must have')),
)


class UserEmailFiltersForm(forms.Form):
    from_ = forms.EmailField(label=_('From'), required=False,
        widget=forms.TextInput(attrs={'class':'long'}))
    to = forms.EmailField(label=_('To'), required=False,
        widget=forms.TextInput(attrs={'class':'long'}))
    subject = forms.CharField(label=_('Subject'), required=False)
    has_the_word = forms.CharField(label=_('Has the words'), required=False)
    does_not_have_the_word = forms.CharField(label=_('Doesn\'t have'),
        required=False)
    has_attachment = forms.ChoiceField(label=_('Has attachment'),
        choices=HAS_ATTACHMENT_CHOICES, required=False)
    label = forms.CharField(label=_('Apply label'), required=False)
    should_mark_as_read = forms.BooleanField(label=_('Mark as read'),
        required=False)
    should_archive = forms.BooleanField(label=_('Archive'), required=False)
    
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
            msg = _('At least one of fields: from, to, subject, has words, '
                'doesn\'t have, has attachment must be filled.')
            raise forms.ValidationError(msg)
        
        if not any(data.get(key) for key in action_fields):
            msg = _('At least one of fields apply label, mark as read, '
                'archive must be filled.')
            raise forms.ValidationError(msg)
        
        return data
    
    def verify_illegal_chars(self, key):
        value = self.cleaned_data[key]
        return enforce_invalid(value, other='[]()$&*')


VACATION_STATE_CHOICES = (
    ('true', _('Enabled')),
    ('false', _('Disabled')),
)

VACATION_CONTACTS_ONLY_CHOICES = (
    ('true', _('Only send a response to people in my Contacts')),
    ('false', _('Send to all')),
)

class UserEmailVacationForm(forms.Form):
    state = forms.ChoiceField(
        label=_('Out of Office AutoReply'), choices=VACATION_STATE_CHOICES,
        widget=forms.Select(attrs={
            'onchange': 'return cr.snippets.vacationStateChanged(this.value);',
        }))
    subject = forms.CharField(max_length=500, required=False)
    message = forms.CharField(widget=forms.Textarea, required=False)
    contacts_only = forms.ChoiceField(
        choices=VACATION_CONTACTS_ONLY_CHOICES, required=False)

    def clean_subject(self):
        enabled = self.cleaned_data.get('state', 'true') == 'true'
        if enabled and not self.cleaned_data['subject']:
            raise forms.ValidationError(
                _('Subject field is required'))
        return self.cleaned_data['subject']

    def clean_message(self):
        enabled = self.cleaned_data.get('state', 'true') == 'true'
        if enabled and not self.cleaned_data['message']:
            raise forms.ValidationError(
                _('Message field is required'))
        return self.cleaned_data['message']

    def clean_contacts_only(self):
        enabled = self.cleaned_data.get('state', 'true') == 'true'
        if enabled and not self.cleaned_data['contacts_only']:
            raise forms.ValidationError(
                _('Message field is required'))
        return self.cleaned_data['contacts_only']


reply_to_c = 'Set %(link_start)sanother%(link_end)s reply to address'
reply_to_e = '%(widget)s %(link_start)sCancel%(link_end)s'


class UserEmailAliasesForm(Form):
    name = forms.CharField(label=_('Name'), max_length=250)
    address = forms.EmailField(label=_('Email address'),
        widget=forms.TextInput(attrs={'class':'long'}))
    reply_to = forms.EmailField(label=_('Reply to'), required=False,
        widget=widgets.SwapWidget(reply_to_c,
            forms.TextInput(attrs={'class':'long'}), reply_to_e))
    make_default = forms.BooleanField(label=_('Make default'), required=False)


################################################################################
#                                    GROUPS                                    #
################################################################################


class GroupForm(Form):
    id = forms.CharField(label=_('Email address'))
    name = forms.CharField(label=_('Name'), required=True)
    email_permission = forms.ChoiceField(label=_('Email permission'),
        choices=consts.GROUP_EMAIL_PERMISSION_CHOICES)
    description = forms.CharField(label=_('Description'), required=False,
        widget=forms.Textarea(attrs=dict(rows=3, cols=30)))
    
    def create(self):
        data = self.cleaned_data
        
        return models.GAGroup(
            id=data['id'],
            name=data['name'],
            email_permission=data['email_permission'],
            description=data['description'])
    
    def populate(self, group):
        data = self.cleaned_data
        
        group.name = data['name']
        group.email_permission = data['email_permission']
        group.description = data['description']
        
        return data['id']
    
    def clean_id(self):
        id = self.cleaned_data['id']
        enforce_valid(id, lower=True, upper=True, digits=True, other='_.-+')
        enforce_some_alnum(id)
        return id
    
    def clean_name(self):
        data = self.cleaned_data['name'].strip()
        if data == '':
            raise forms.ValidationError(_('Group name is required.'))
        return data


owner_c = '%(link_start)sAdd%(link_end)s another owner'
owner_e = '%(widget)s %(link_start)sCancel%(link_end)s'
member_c = '%(link_start)sAdd%(link_end)s another member'
member_e = '%(widget)s %(link_start)sCancel%(link_end)s'


class GroupMembersForm(forms.Form):
    owner = forms.EmailField(label=_('Owners'), required=False,
        widget=widgets.SwapWidget(owner_c,
            forms.TextInput(attrs={'class':'long', 'id':'owner'}), owner_e))
    member = forms.EmailField(label=_('Members'), required=False,
        widget=widgets.SwapWidget(member_c,
            forms.TextInput(attrs={'class':'long', 'id':'member'}), member_e))


################################################################################
#                                    ROLES                                     #
################################################################################


PERMISSION_NAMES = crauth.permissions.permission_names(False)
OBJECT_TYPES = (
    ('users', _('Manage Users'), (
        ('gauser', _('General')),
        ('gausersettings', _('Settings')),
        ('gauserfilters', _('Filters')),
        ('gausersendas', _('Send as')),
        ('gauservacation', _('Vacation responder')),
    )),
    ('groups', _('Manage Groups'), (
        ('gagroup', _('General')),
    )),
    ('roles', _('Manage Roles'), (
        ('role', _('General')),
    )),
    ('shared_contacts', _('Manage Shared Contacts'), (
        ('sharedcontact', _('General')),
    )),
    ('calendar_resources', _('Manage Calendar Resources'), (
        ('calendarresource', _('General')),
    )),
)


class ObjectTypeFields(object):
    def __init__(self, form, obj_type, name=None):
        self.form = form
        self.obj_type = obj_type
        self.name = name or obj_type
    
    def obj_name(self):
        return 
    
    def add(self):
        return self.get('add_%s' % self.obj_type)
    
    def change(self):
        return self.get('change_%s' % self.obj_type)
    
    def read(self):
        return self.get('read_%s' % self.obj_type)
    
    def get(self, key):
        try:
            return self.form[key]
        except KeyError:
            return None


class RoleForm(forms.Form):
    name = forms.CharField(label=_('Name'), required=True)
    
    def __init__(self, *args, **kwargs):
        super(forms.Form, self).__init__(*args, **kwargs)
        
        self.sections = dict()
        
        perms = dict()
        for perm in PERMISSION_NAMES:
            action, obj_type = perm.split('_')
            
            actions = perms[obj_type] if obj_type in perms else set()
            actions.add(action)
            perms[obj_type] = actions
        
        for section in OBJECT_TYPES:
            self._add_section(section, perms)

    def _data_to_permissions(self):
        data = self.cleaned_data

        permissions = set()
        for perm in PERMISSION_NAMES:
            if perm in data and data[perm]:
                permissions.add(perm)
                if perm.startswith('change_') or perm.startswith('add_'):
                    permissions.add(perm.replace('change_', 'read_').replace(
                        'add_', 'read_'))
        return list(permissions)
    
    def create(self, domain):
        return crauth.models.Role(
            parent=domain, name=self.cleaned_data['name'],
            permissions=self._data_to_permissions())
    
    def populate(self, role):
        role.name = self.cleaned_data['name']
        role.permissions = self._data_to_permissions()
    
    def _add_section(self, section, perms):
        section_obj = dict(name=section[1], groups=[])
        
        # iterating through section groups
        for obj_type, name in section[2]:
            actions = list(perms[obj_type])
            actions.sort()
            
            # adding fields to the form
            for action in actions:
                field = self._add_field(obj_type, action)
            
            # adding group to section
            group = ObjectTypeFields(self, obj_type, name=name)
            section_obj['groups'].append(group)
        self.sections[section[0]] = section_obj
    
    def _add_field(self, obj_type, action):
        field_name = '%s_%s' % (action, obj_type)
        field = forms.BooleanField(
            required=False, widget=forms.CheckboxInput(
                attrs={
                    'class': 'perm_%s' % action,
                    'onchange': 'cr.snippets.createRolePermissionChanged(this);',
                }))
        self.fields[field_name] = field
        return field
    
    def clean_name(self):
        name = self.cleaned_data['name'].strip()
        if name == '':
            raise forms.ValidationError(_('Role name is required.'))
        if not hasattr(self, 'old_name') or name != self.old_name:
            role = Role.for_domain(crauth.users.get_current_domain()).filter(
                'name', name).get()
            if role or name == _('Administrator'):
                raise forms.ValidationError(_('Role with this name already exists.'))
        return name


################################################################################
#                               SHARED CONTACTS                                #
################################################################################


emails_c = '%(link_start)sAdd email%(link_end)s'
emails_e = 'Enter email:<br/>%(widget)s %(link_start)sCancel%(link_end)s'
phone_numbers_c = '%(link_start)sAdd phone number%(link_end)s'
phone_numbers_e = 'Enter phone number:<br/>%(widget)s %(link_start)sCancel%(link_end)s'


class SharedContactForm(forms.Form):
    full_name = forms.CharField(label=_('Display name'))
    real_name = fields.RealNameField(label=_('Real name'), required=False)
    notes = forms.CharField(label=_('Notes'), required=False,
        widget=forms.Textarea(attrs=dict(rows=3, cols=30)))
    company = forms.CharField(label=_('Company'), required=False)
    role = forms.CharField(label=_('Role'), required=False)
    
    # email field to show when creating contact
    email = forms.EmailField(label=_('Email'), required=False,
        widget=forms.TextInput(attrs={'class':'long'}))
    # emails filed to show when editing contact
    emails = forms.EmailField(label=_('Emails'), required=False,
        widget=widgets.SwapWidget(emails_c,
            forms.TextInput(attrs={'class':'long'}), emails_e))
    
    # phone number field to show when creating contact
    phone_number = forms.CharField(label=_('Phone number'), required=False)
    # phone numbers field to show when editing contact
    phone_numbers = forms.CharField(label=_('Phone numbers'), required=False,
        widget=widgets.SwapWidget(phone_numbers_c,
            forms.TextInput(), phone_numbers_e))
    
    def create(self):
        data = self.cleaned_data
        
        name = models.Name(
            full_name=data['full_name'], name_prefix=data['real_name'][0],
            given_name=data['real_name'][1], family_name=data['real_name'][2])
        
        email = data['email']
        emails = [self._email(email)] if email else []
        
        phone_number = data['phone_number']
        phone_numbers = [self._phone_number(phone_number)] if phone_number else []
        
        contact = models.SharedContact(
            name=name, notes=data['notes'],
            emails=emails, phone_numbers=phone_numbers)

        company, role = data['company'], data['role']
        if company or role:
            contact.organization = models.Organization(
                name=company, title=role)
            contact.organization.save()

        return contact
    
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
    
    def clean(self):
        data = self.cleaned_data
        company = data.get('company')
        role = data.get('role')
        
        # role filled => company must be filled
        if not company and role:
            msg = _('Company is required if role is not empty.')
            self._errors['company'] = ErrorList([msg])
            
            data.pop('company', None)
            data.pop('role', None)
        
        return data


################################################################################
#                              CALENDAR RESOURCES                              #
################################################################################


class CalendarResourceForm(forms.Form):
    common_name = forms.CharField(_('Name'))
    type = forms.CharField(_('Type'), required=False)
    description = forms.CharField(_('Description'), required=False,
        widget=forms.Textarea(attrs=dict(rows=3, cols=30)))
    
    def create(self, id):
        data = self.cleaned_data
        
        return models.CalendarResource(
            id=id, common_name=data['common_name'], type=data['type'],
            description=data['description'])
    
    def populate(self, resource):
        data = self.cleaned_data
        
        resource.common_name = data['common_name']
        resource.type = data['type']
        resource.description = data['description']
        
    def clean_common_name(self):
        name = self.cleaned_data['common_name'].strip()
        if name == '':
            raise forms.ValidationError(_('Name is required.'))
        return name


################################################################################
#                              SETTINGS                                        #
################################################################################


class SettingsForm(forms.ModelForm):
    class Meta:
        model = models.Preferences
        fields = ('items_per_page',)

    ITEMS_PER_PAGE_CHOICES = (
        (20, '20'),
        (50, '50'),
        (100, '100'),
    )
    items_per_page = forms.TypedChoiceField(
        choices=ITEMS_PER_PAGE_CHOICES, coerce=int,
        help_text=_('How many items to show at once on listing pages.'))

