import logging
from appengine_django.models import BaseModel
from google.appengine.ext import db
from google.appengine.api import memcache
from crauth.licensing import LICENSE_STATES, STATE_ACTIVE


class Association(db.Model):
    url = db.LinkProperty()
    handle = db.StringProperty()
    association = db.TextProperty()


class AppsDomain(BaseModel):
    CACHE_TIME = 2 * 60 * 60 # we cache activity state for 2 hours

    domain = db.StringProperty(required=True)
    admin_email = db.StringProperty()
    # apparently it's only possible to send ClientLogin passwords in clear text,
    # so no hashing
    admin_password = db.StringProperty()
    license_state = db.StringProperty(choices=LICENSE_STATES)
    is_enabled = db.BooleanProperty(default=False)
    is_independent = db.BooleanProperty(default=False)

    def is_active(self):
        return self.is_enabled and (
            self.is_independend or self.license_state == STATE_ACTIVE)

    @classmethod
    def is_arbitrary_domain_active(cls, domain):
        from crauth.licensing import LicensingClient
        apps_domain = AppsDomain.get_by_key_name(domain)
        if apps_domain is not None and apps_domain.is_active():
            return True
        AppsDomain.get_or_insert(
            key_name=domain,
            domain=domain,
        )
        client = LicensingClient()
        result = client.get_domain_info(domain).entry[0]
        return result.content.entity.state.text == STATE_ACTIVE


