import logging
import pickle
from appengine_django.models import BaseModel
from google.appengine.ext import db


def _model_kwargs(model_instance, fields):
    kwargs = {}
    for field in fields:
        kwargs[field] = getattr(model_instance, field)
    return kwargs


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
    domain = db.StringProperty()
    model_class = db.StringProperty()


# Cache models

class _CacheBase(BaseModel):
    class Meta:
        # appengine_django actually overwrites this property to False, but we
        # leave it here as an indication that this model shouldn't be used
        # directly.
        abstract = True

    _domain = db.StringProperty()
    _gdata_key_name = db.StringProperty()
    _atom = db.BlobProperty()
    _index = db.ReferenceProperty(GDataIndex)
    _updated_on = db.DateTimeProperty(auto_now=True)

    @classmethod
    def model_to_kwargs(cls, model_instance, **kwargs):
        kwargs = dict(kwargs)
        props = [prop for prop in cls._properties.keys()
                 if not prop.startswith('_')]
        kwargs.update(_model_kwargs(model_instance, props))
        return kwargs

    @classmethod
    def from_model(cls, model_instance, **kwargs):
        kwargs = cls.model_to_kwargs(model_instance, **kwargs)
        if kwargs.has_key('_atom'):
            kwargs['_atom'] = pickle.dumps(
                kwargs['_atom'], pickle.HIGHEST_PROTOCOL)
        return cls(**kwargs)

    def update(self, model_instance):
        kwargs = self.model_to_kwargs(model_instance)
        for key, value in kwargs.iteritems():
            setattr(self, key, value)
        self._atom = pickle.dumps(model_instance._atom, pickle.HIGHEST_PROTOCOL)


class UserCache(_CacheBase):
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


class GroupCache(_CacheBase):
    id = db.StringProperty()
    name = db.StringProperty()
    description = db.StringProperty()
    email_permission = db.StringProperty()


class NicknameCache(_CacheBase):
    nickname = db.StringProperty()
    user_name = db.StringProperty()
    user = db.StringProperty()

    @classmethod
    def model_to_kwargs(cls, model_instance, **kwargs):
        kwargs = dict(kwargs)
        kwargs.update({
            'nickname': model_instance.nickname,
            'user_name': model_instance.user_name,
            'user': model_instance.user_name,
        })
        return kwargs


class SharedContactCache(_CacheBase):
    name = db.StringListProperty()
    title = db.StringProperty()
    notes = db.StringProperty()
    birthday = db.DateProperty()
    emails = db.StringListProperty()
    phone_numbers = db.StringListProperty()
    postal_addresses = db.StringListProperty()
    organization = db.StringProperty()

    @classmethod
    def model_to_kwargs(cls, model_instance, **kwargs):
        kwargs = dict(kwargs)
        name = model_instance.name and [
            getattr(model_instance.name, attr)
            for attr in ('given_name', 'family_name')] or []
        name = [x for x in name if x]
        emails = [email.address for email in model_instance.emails]
        phone_numbers = [number.number
                         for number in model_instance.phone_numbers]
        addresses = [address.address
                     for address in model_instance.postal_addresses]
        if model_instance.organization:
            organization = model_instance.organization.name
        else:
            organization = None
        kwargs.update({
            'name': name,
            'emails': emails,
            'phone_numbers': phone_numbers,
            'addresses': addresses,
            'organization': organization,
        })
        kwargs.update(_model_kwargs(model_instance, (
            'title', 'notes', 'birthday',
        )))
        return kwargs

