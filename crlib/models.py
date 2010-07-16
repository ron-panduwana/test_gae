from appengine_django.models import BaseModel
from google.appengine.ext import db


class LastCacheUpdate(BaseModel):
    last_updated = db.DateTimeProperty(auto_now=True)


class GDataIndex(BaseModel):
    # key_name consists of: domain_name:mapper_class[:page]
    # where page part is to be omitted for the first page
    page_hash = db.StringProperty(indexed=False)
    etag = db.StringProperty(indexed=False)
    hashes = db.StringListProperty(indexed=False)
    keys = db.StringListProperty()
    last_updated = db.DateTimeProperty()


class UserCache(BaseModel):
    # key_name consists of: domain_name:atom_hash
    # or atom_hash alone
    id = db.StringProperty()
    title = db.StringProperty()
    user_name = db.StringProperty(required=True)
    given_name = db.StringProperty(required=True)
    family_name = db.StringProperty(required=True)
    suspended = db.BooleanProperty(default=False)
    admin = db.BooleanProperty(default=False)
    agreed_to_terms = db.BooleanProperty()
    quota = db.IntegerProperty()
    change_password = db.BooleanProperty(default=False)
    updated_on = db.DateTimeProperty(auto_now=True)


class NicknameCache(BaseModel):
    nickname = db.StringProperty()
    user_name = db.StringProperty()


class SharedContactNameCache(BaseModel):
    given_name = db.StringProperty()
    family_name = db.StringProperty()
    additional_name = db.StringProperty()
    name_prefix = db.StringProperty()
    name_suffix = db.StringProperty()
    full_name = db.StringProperty()


class SharedContactEmailCache(BaseModel):
    address = db.EmailProperty()
    label = db.StringProperty()
    rel = db.StringProperty()
    primary = db.BooleanProperty(default=False)


class SharedContactCache(BaseModel):
    name = db.ReferenceProperty(SharedContactNameCache)
    title = db.StringProperty()
    notes = db.StringProperty()
    birthday = db.DateProperty()
    emails = db.ListProperty(db.Key)


#class NicknameCache(BaseModel):
#    nickname = db.StringProperty(required=True)
#    user_name = db.StringProperty()
#    user = db.ReferenceProperty(UserCache)
#    updated_on = db.DateTimeProperty(auto_now=True)

