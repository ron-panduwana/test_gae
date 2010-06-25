from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from appengine_django.models import BaseModel
from google.appengine.ext import db
from crlib import gdata_wrapper as gd
from crlib import mappers
from crlib.signals import gauser_renamed
from crauth import users


# Datastore models

class Preferences(BaseModel):
    items_per_page = db.IntegerProperty(default=50)
    language = db.StringProperty(default='en')

    @classmethod
    def for_current_user(cls):
        user = users.get_current_user()
        if user:
            return cls.for_user(user)

    @classmethod
    def for_user(cls, user):
        return cls.get_or_insert(key_name=user.email())

    @classmethod
    def for_email(cls, email):
        return cls.get_or_insert(key_name=email)

def gauser_renamed_callback(sender, **kwargs):
    """ Copy Preferences model instance of old user to the new instance.

    `sender` parameter denotes domain name of the user.
    `**kwargs` contains `old_name` and `new_name` parameters.

    """
    old_email = '%s@%s' % (kwargs['old_name'], sender)
    new_email = '%s@%s' % (kwargs['new_name'], sender)
    preferences = Preferences.get_by_key_name(old_email)
    if preferences:
        new_preferences = Preferences(
            key_name=new_email,
            language=preferences.language)
        new_preferences.put()
        preferences.delete()

gauser_renamed.connect(gauser_renamed_callback)


# GData pseudo-models

class GAUser(gd.Model):
    Mapper = mappers.UserEntryMapper()
    class Meta:
        permissions = (
            ('read_gauser', _('View users in your domain')),
            ('add_gauser', _('Create users in your domain')),
            ('change_gauser', _('Modify users in your domain')),
            ('change_gausersettings', _('Modify users in your domain')),
            ('change_gauserfilters', _('Modify users in your domain')),
            ('change_gausersendas', _('Modify users in your domain')),
        )

    id = gd.StringProperty('id.text', read_only=True)
    title = gd.StringProperty('title.text', read_only=True)
    user_name = gd.StringProperty('login.user_name', required=True)
    given_name = gd.StringProperty('name.given_name', required=True)
    family_name = gd.StringProperty('name.family_name', required=True)
    password = gd.PasswordProperty('login.password')
    suspended = gd.BooleanProperty('login.suspended', default=False)
    admin = gd.BooleanProperty('login.admin', default=False)
    agreed_to_terms = gd.BooleanProperty(
        'login.agreed_to_terms', read_only=True)
    quota = gd.IntegerProperty('quota.limit')
    change_password = gd.BooleanProperty('login.change_password', default=False)
    email_settings = mappers.EmailSettingsProperty()

    @classmethod
    def get_current_user(cls):
        user = users.get_current_user()
        if user:
            return cls.get_by_key_name(user.email().rpartition('@')[0])

    def get_full_name(self):
        return '%s %s' % (self.given_name, self.family_name)


class GAGroupMember(gd.Model):
    Mapper = mappers.MemberEntryMapper()

    id = gd.StringProperty('memberId', required=True)
    direct_member = gd.BooleanProperty('directMember')
    type = gd.StringProperty('memberType')

    @classmethod
    def from_user(cls, user):
        domain = users.get_current_user().domain_name
        return GAGroupMember(
            id='%s@%s' % (user.user_name, domain)).save()

    def __unicode__(self):
        return self.id

    def is_user(self):
        return self.to_user() is not None

    def to_user(self):
        user_name = self.id.partition('@')[0]
        return GAUser.get_by_key_name(user_name)

    def is_group(self):
        return self.to_group() is not None

    def to_group(self):
        return GAGroup.get_by_key_name(self.id)


class GAGroupOwner(gd.Model):
    Mapper = mappers.OwnerEntryMapper()

    email = gd.StringProperty('email', required=True)
    type = gd.StringProperty('type')

    @classmethod
    def from_user(cls, user):
        domain = users.get_current_user().domain_name
        return GAGroupOwner(
            email='%s@%s' % (user.user_name, domain)).save()

    def is_user(self):
        return self.to_user() is not None

    def to_user(self):
        user_name = self.email.partition('@')[0]
        return GAUser.get_by_key_name(user_name)


class GAGroup(gd.Model):
    Mapper = mappers.GroupEntryMapper()
    class Meta:
        permissions = (
            ('read_gagroup', _('View groups in your domain')),
            ('add_gagroup', _('Create groups in your domain')),
            ('change_gagroup', _('Modify groups in your domain')),
        )

    id = gd.StringProperty('groupId', required=True)
    name = gd.StringProperty('groupName', required=True)
    description = gd.StringProperty('description')
    email_permission = gd.StringProperty(
        'emailPermission', required=True,
        choices=mappers.GROUP_EMAIL_PERMISSIONS)
    members = gd.ListProperty(GAGroupMember, 'members')
    owners = gd.ListProperty(GAGroupOwner, 'owners')

    def __unicode__(self):
        return self.name

    def is_user_member(self, user):
        # TODO: We could use IsMember() GData call, but I don't know how to
        # handle it yet
        return GAGroupMember.from_user(user) in self.members

    @classmethod
    def add_user_to_groups(cls, user, group_ids):
        groups = GAGroup.all().fetch(1000)
        member = GAGroupMember.from_user(user)
        for group in groups:
            if group.id in group_ids and not member in group.members:
                group.members.append(member)
                group.save()
    
    def get_pure_id(self):
        return self.id.partition('@')[0]


class GANickname(gd.Model):
    Mapper = mappers.NicknameEntryMapper()
    class Meta:
        permissions = ()

    nickname = gd.StringProperty('nickname.name', required=True)
    user_name = gd.StringProperty('login.user_name')
    user = gd.ReferenceProperty(
        GAUser, 'login.user_name', required=True, collection_name='nicknames')
    
    def __unicode__(self):
        return self.nickname


class Email(gd.Model):
    Mapper = mappers.EmailMapper()

    address = gd.StringProperty('address', required=True)
    label = gd.StringProperty('label', required=False)
    rel = mappers.RelProperty()
    primary = gd.BooleanProperty('primary', default=False)


class PhoneNumber(gd.Model):
    Mapper = mappers.PhoneNumberMapper()

    number = gd.StringProperty('text', required=True)
    label = gd.StringProperty('label', required=False)
    rel = mappers.RelProperty(mappers.PHONE_TYPES)
    primary = gd.BooleanProperty('primary', default=False)


class PostalAddress(gd.Model):
    Mapper = mappers.PostalAddressMapper()

    address = gd.StringProperty('text', required=True)
    label = gd.StringProperty('label', required=False)
    rel = mappers.RelProperty()
    primary = gd.BooleanProperty('primary', default=False)


class Name(gd.Model):
    Mapper = mappers.NameMapper()

    given_name = gd.StringProperty('given_name.text')
    family_name = gd.StringProperty('family_name.text')
    additional_name = gd.StringProperty('additional_name.text')
    name_prefix = gd.StringProperty('name_prefix.text')
    name_suffix = gd.StringProperty('name_suffix.text')
    full_name = gd.StringProperty('full_name.text')


class Organization(gd.Model):
    Mapper = mappers.OrganizationMapper()

    name = gd.StringProperty('name.text', required=False)
    rel = mappers.RelProperty(mappers.ORGANIZATION_TYPES,
                              default=mappers.ORGANIZATION_TYPES[0][0])
    primary = gd.BooleanProperty('primary', default=False)
    title = gd.StringProperty('title.text', required=False)
    job_description = gd.StringProperty(
        'job_description.text', required=False)
    department = gd.StringProperty('department.text', required=False)
    symbol = gd.StringProperty('symbol.text', required=False)


class Website(gd.Model):
    Mapper = mappers.WebsiteMapper()

    href = gd.StringProperty('href')
    rel = mappers.RelProperty(mappers.WEBSITE_TYPES)
    label = gd.StringProperty('label', required=False)
    primary = gd.BooleanProperty('primary', default=False)


class SharedContact(gd.Model):
    Mapper = mappers.SharedContactEntryMapper()
    class Meta:
        permissions = (
            ('read_sharedcontact', _('View shared contacts in your domain')),
            ('add_sharedcontact', _('Create shared contacts in your domain')),
            ('change_sharedcontact',
             _('Modify shared contacts in your domain')),
        )

    name = gd.EmbeddedModelProperty(Name, 'name', required=False)
    title = gd.StringProperty('title.text', required=False, read_only=True)
    notes = gd.StringProperty('content.text')
    birthday = gd.DateProperty('birthday.when', required=False)
    emails = gd.ListProperty(Email, 'email', required=False)
    phone_numbers = gd.ListProperty(
        PhoneNumber, 'phone_number', required=False)
    postal_addresses = gd.ListProperty(
        PostalAddress, 'postal_address', required=False)
    organization = gd.EmbeddedModelProperty(
        Organization, 'organization', required=False)
    websites = gd.ListProperty(Website, 'website', required=False)
    extended_properties = gd.ExtendedPropertyMapping(
        'extended_property', required=False)
    
    def __unicode__(self):
        return u'<SharedContact: %s>' % self.title


class CalendarResource(gd.Model):
    Mapper = mappers.CalendarResourceEntryMapper()
    class Meta:
        permissions = (
            ('read_calendarresource',
             _('View calendar resources in your domain')),
            ('add_calendarresource',
             _('Create calendar resources in your domain')),
            ('change_calendarresource',
             _('Modify calendar resources in your domain')),
        )

    id = gd.StringProperty('resource_id', required=True)
    common_name = gd.StringProperty('resource_common_name', required=True)
    description = gd.StringProperty('resource_description')
    type = gd.StringProperty('resource_type')

