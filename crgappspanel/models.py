from __future__ import with_statement
from appengine_django.models import BaseModel
from google.appengine.ext import db
from crlib import gdata_wrapper as gd


class GAUser(gd.Model):
    Mapper = gd.UserEntryMapper()

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
    change_password= gd.BooleanProperty('login.change_password', default=False)
    
    def get_full_name(self):
        return '%s %s' % (self.given_name, self.family_name)


class GANickname(gd.Model):
    Mapper = gd.NicknameEntryMapper()

    nickname = gd.StringProperty('nickname.name', required=True)
    user_name = gd.StringProperty('login.user_name')
    user = gd.ReferenceProperty(
        GAUser, 'login.user_name', required=True, collection_name='nicknames')
    
    def __unicode__(self):
        return self.nickname


class ExtendedProperty(gd.Model):
    Mapper = gd.ExtendedPropertyMapper()

    name = gd.StringProperty('name', required=True)
    value = gd.StringProperty('value', required=True)


class ContactEmail(gd.Model):
    Mapper = gd.ContactEmailMapper()

    address = gd.StringProperty('address', required=True)
    rel = gd.EmailTypeProperty('rel', required=True, default='work')
    primary = gd.BooleanProperty('primary', default=False)


class SharedContact(gd.Model):
    Mapper = gd.SharedContactEntryMapper()

    name = gd.StringProperty('title.text', required=True)
    notes = gd.StringProperty('content.text')
    emails = gd.ListProperty(ContactEmail, 'email', required=True)
    extended_properties = gd.ListProperty(
        ExtendedProperty, 'extended_property')

    def __unicode__(self):
        return u'<SharedContact: %s>' % self.name


class TestModel(BaseModel):
    user = gd.ReferenceProperty(GAUser)


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

