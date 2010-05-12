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

    #: *Google Apps* domain. This value is also set as ``key_name`` of the given
    #: model instance for faster datastore reads.
    domain = db.StringProperty(required=True)
    #: Email of domain administrator account.
    admin_email = db.StringProperty()
    #: Password of domain administrator account. This value should be considered
    #: **write-only** and never shown to users. Unfortunately *GData API*
    #: doesn't allow to use hashed password in the *ClientLogin* authentication
    #: method which would greatly improve the overall security.
    admin_password = db.StringProperty()
    #: Value of this property is updated by
    #: :func:`crauth.views.handle_license_updates` via cron job.
    #: Allowed values are defined in :const:`crauth.licensing.LICENSE_STATES`.
    license_state = db.StringProperty(choices=LICENSE_STATES)
    #: This property takes precedence before both :attr:`is_independent` and
    #: :attr:`license_state`. If set to ``False`` the domain will not be able to
    #: accees the application.
    is_enabled = db.BooleanProperty(default=False)
    #: If set to ``True`` the domain is managed manually and Licensing API is
    #: not used.
    is_independent = db.BooleanProperty(default=False)

    def is_active(self):
        return self.is_enabled and (
            self.is_independent or self.license_state == STATE_ACTIVE)

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


