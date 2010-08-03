import logging
import pickle
import re
from appengine_django.models import BaseModel
from google.appengine.ext import db
from google.appengine.api import memcache


def _model_kwargs(model_instance, fields):
    kwargs = {}
    for field in fields:
        value = getattr(model_instance, field)
        if isinstance(value, str):
            value = value.decode('utf8')
        if isinstance(value, unicode) and len(value) >= 500:
            value = value[:500]
        kwargs[field] = value
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
    USERS_PER_JOB = 5

    id = db.StringProperty()
    user_name = db.StringProperty(required=True)
    given_name = db.StringProperty(required=True)
    family_name = db.StringProperty(required=True)
    suspended = db.BooleanProperty(default=False)
    admin = db.BooleanProperty(default=False)
    agreed_to_terms = db.BooleanProperty()
    quota = db.IntegerProperty()
    change_password = db.BooleanProperty(default=False)

    @classmethod
    def additional_cache(cls, items, index, domain):
        import math
        from django.core.urlresolvers import reverse
        from google.appengine.api.labs import taskqueue
        from crlib import cache

        if memcache.get('nickname_lock:' + index.key().name()):
            return

        memcache.set('nickname_lock:' + index.key().name(), True, 58 * 60)

        jobs = int(math.ceil(float(len(items)) / cls.USERS_PER_JOB))
        key_parts = index.key().name().split(':')
        key_name = '%s:GANickname' % domain
        if len(key_parts) == 3:
            key_name += ':' + key_parts[-1]
        nick_index = GDataIndex.get_or_insert(
            key_name=key_name,
            domain=domain,
            model_class='GANickname',
            last_updated=cache.MIN_DATETIME,
        )
        for i in range(jobs):
            users = items[i * cls.USERS_PER_JOB:i * cls.USERS_PER_JOB +
                          cls.USERS_PER_JOB]
            if users:
                taskqueue.add(url=reverse('precache_nicknames'), params={
                    'users': ':'.join([user.user_name for user in users]),
                    'domain': domain,
                    'index': key_name,
                })


class GroupCache(_CacheBase):
    id = db.StringProperty()
    name = db.StringProperty()
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


RE_SPLIT = re.compile(r'[^\w\d]+', re.UNICODE)

class SharedContactCache(_CacheBase):
    name = db.StringProperty()
    title = db.StringProperty()
    birthday = db.DateProperty()
    emails = db.StringListProperty()
    phone_numbers = db.StringListProperty()
    postal_addresses = db.StringListProperty()
    organization = db.StringProperty()
    notes = db.StringListProperty()
    search_index = db.StringListProperty()
    name_index = db.StringListProperty()

    @classmethod
    def model_to_kwargs(cls, model_instance, **kwargs):
        kwargs = dict(kwargs)
        name_index = model_instance.name and [
            getattr(model_instance.name, attr)
            for attr in ('given_name', 'family_name')] or []
        name = ' '.join([x.lower() for x in reversed(name_index) if x])
        name_index = [x.lower() for x in name_index if x] or ['']
        name = name and name[:500]
        emails = sorted([email.address for email in model_instance.emails])
        emails = emails or ['']
        phone_numbers = sorted([number.number
                                for number in model_instance.phone_numbers])
        phone_numbers = phone_numbers or ['']
        addresses = [address.address
                     for address in model_instance.postal_addresses]
        if model_instance.organization:
            organization = model_instance.organization.name
        else:
            organization = None
        organization = organization and organization.lower() or ''

        def _filter(l):
            return [item[:500].lower() for item in l if item]

        notes = RE_SPLIT.split(model_instance.notes or '')
        notes = list(set(_filter(notes)))

        index = []
        index += RE_SPLIT.split(model_instance.name.full_name or '')
        index += emails
        index += phone_numbers
        index += addresses
        index += RE_SPLIT.split(organization or '')
        index = list(set(_filter(index)))

        kwargs.update({
            'name': name,
            'name_index': name_index,
            'emails': emails,
            'phone_numbers': phone_numbers,
            'addresses': addresses,
            'organization': organization,
            'notes': notes,
            'search_index': index,
        })
        kwargs.update(_model_kwargs(model_instance, (
            'title', 'birthday',
        )))
        return kwargs

