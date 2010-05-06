from django.conf import settings
from appengine_django.models import BaseModel
from google.appengine.ext import db
from crlib import gdata_wrapper as gd
from crlib import mappers
from auth import users


class GAUser(gd.Model):
    Mapper = mappers.UserEntryMapper()

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
    
    def get_full_name(self):
        return '%s %s' % (self.given_name, self.family_name)


class GAGroupMember(gd.Model):
    Mapper = mappers.MemberEntryMapper()

    id = gd.StringProperty('memberId', required=True)
    direct_member = gd.BooleanProperty('directMember')
    type = gd.StringProperty('memberType')

    @classmethod
    def from_user(cls, user):
        domain = users.get_current_user().domain().domain
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
        domain = users.get_current_user().domain().domain
        return GAGroupOwner(
            email='%s@%s' % (user.user_name, domain)).save()

    def is_user(self):
        return self.to_user() is not None

    def to_user(self):
        user_name = self.email.partition('@')[0]
        return GAUser.get_by_key_name(user_name)


class GAGroup(gd.Model):
    Mapper = mappers.GroupEntryMapper()

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
    rel = mappers.RelProperty(mappers.ORGANIZATION_TYPES)
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

    id = gd.StringProperty('resource_id', required=True)
    common_name = gd.StringProperty('resource_common_name')
    description = gd.StringProperty('resource_description')
    type = gd.StringProperty('resource_type')


class Role(BaseModel):
    name = db.StringProperty()
    description = db.StringProperty()
    #privileges = db.ListProperty()

    @classmethod
    def get_by_name(cls, name):
        return cls.get_by_key_name('role:%s' % name)

    @classmethod
    def create(cls, name, description):
        def txn():
            role = cls(
                key_name='role:%s' % name,
                name=name,
                description=description)
            role.put()
            return role
        return db.run_in_transaction(txn)

    @classmethod
    def get_user_role(cls, user):
        return _UserRoleMapping.get_by_key_name(user.id).role

    def add_user(self, user):
        def txn(user_id, role_key):
            mapping = _UserRoleMapping(
                key_name=user.id,
                role=role_key)
            mapping.put()
            return mapping
        db.run_in_transaction(user.id, self.key())


class _UserRoleMapping(BaseModel):
    roles = db.ListProperty(db.Key)

