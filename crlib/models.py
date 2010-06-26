from appengine_django.models import BaseModel
from google.appengine.ext import db


class LastCacheUpdate(BaseModel):
    last_updated = db.DateTimeProperty(auto_now=True)


class GDataIndex(BaseModel):
    page_hash = db.StringProperty(indexed=False)
    hashes = db.StringListProperty(indexed=False)
    keys = db.StringListProperty()


class UserCache(BaseModel):
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
    nickname = db.StringProperty(required=True)
    user_name = db.StringProperty()
    user = db.ReferenceProperty(UserCache)
    updated_on = db.DateTimeProperty(auto_now=True)

