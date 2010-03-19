from __future__ import with_statement
from appengine_django.models import BaseModel
from google.appengine.ext import db
from crlib import gdata


def _tmp_get_credentials():
    credentials = []
    with open('google_apps.txt') as f:
        for line in f:
            credentials.append(line.strip())
    return credentials[:3]
_credentials = _tmp_get_credentials()


class GAUser(gdata.Model):
    Mapper = gdata.UserEntryMapper(*_credentials)

    id = gdata.StringProperty('id.text', read_only=True)
    user_name = gdata.StringProperty('login.user_name', required=True)
    given_name = gdata.StringProperty('name.given_name', required=True)
    family_name = gdata.StringProperty('name.family_name', required=True)
    password = gdata.PasswordProperty('login.password')
    suspended = gdata.BooleanProperty('login.suspended', default=False)
    admin = gdata.BooleanProperty('login.admin', default=False)

    def key(self):
        return self.user_name

    def __repr__(self):
        return '<GAUser: %s>' % self.user_name


class GANickname(gdata.Model):
    Mapper = gdata.NicknameEntryMapper(*_credentials)

    nickname = gdata.StringProperty('nickname.name', required=True)
    user = gdata.ReferenceProperty(
        GAUser, 'login.user_name', required=True,
        collection_name='nicknames')

    def key(self):
        return self.nickname

    def __repr__(self):
        return '<GANickname: %s>' % self.nickname


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

