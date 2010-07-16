import logging
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


# Cache models

class UserCache(BaseModel):
    # key_name consists of: domain_name:atom_hash
    # or atom_hash alone
    domain = db.StringProperty()
    _gdata_key_name = db.StringProperty()
    atom = db.BlobProperty()

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

    @classmethod
    def from_model(cls, model_instance, **kwargs):
        return cls(
            id=model_instance.id,
            title=model_instance.title,
            user_name=model_instance.user_name,
            given_name=model_instance.given_name,
            family_name=model_instance.family_name,
            suspended=model_instance.suspended,
            admin=model_instance.admin,
            agreed_to_terms=model_instance.agreed_to_terms,
            quota=model_instance.quota,
            change_password=model_instance.change_password,
            **kwargs
        )


class GroupCache(BaseModel):
    domain = db.StringProperty()
    _gdata_key_name = db.StringProperty()
    atom = db.BlobProperty()

    id = db.StringProperty()
    name = db.StringProperty()
    description = db.StringProperty()
    email_permission = db.StringProperty()

    @classmethod
    def from_model(cls, model_instance, **kwargs):
        return cls(
            id=model_instance.id,
            name=model_instance.name,
            description=model_instance.description,
            email_permission=model_instance.email_permission,
            **kwargs
        )


class NicknameCache(BaseModel):
    domain = db.StringProperty()
    _gdata_key_name = db.StringProperty()
    atom = db.BlobProperty()

    nickname = db.StringProperty()
    user_name = db.StringProperty()
    user = db.StringProperty()

    @classmethod
    def from_model(cls, model_instance, **kwargs):
        return cls(
            nickname=model_instance.nickname,
            user_name=model_instance.user_name,
            user=model_instance.user_name,
            **kwargs
        )


class SharedContactCache(BaseModel):
    domain = db.StringProperty()
    _gdata_key_name = db.StringProperty()
    atom = db.BlobProperty()
    name = db.StringListProperty()
    title = db.StringProperty()
    notes = db.StringProperty()
    birthday = db.DateProperty()
    emails = db.StringListProperty()
    phone_numbers = db.StringListProperty()
    postal_addresses = db.StringListProperty()
    organization = db.StringProperty()

    @classmethod
    def from_model(cls, model_instance, **kwargs):
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

        return cls(
            name=name,
            title=model_instance.title,
            notes=model_instance.notes,
            birthday=model_instance.birthday,
            emails=emails,
            phone_numbers=phone_numbers,
            postal_addresses=addresses,
            organization=organization,
            **kwargs
        )

