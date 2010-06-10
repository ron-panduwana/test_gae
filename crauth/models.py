import logging
from appengine_django.models import BaseModel
from django.core.urlresolvers import reverse
from google.appengine.ext import db
from google.appengine.api import memcache
from crauth.licensing import LICENSE_STATES, STATE_ACTIVE
from crauth.permissions import class_prepared_callback
from crlib.signals import class_prepared


class_prepared.connect(class_prepared_callback)


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
    #: Security token which should be sent to Google Apps domain administrator
    #: for him to perform Powerpanel installation w/o Google Marketplace
    #: machinery.
    installation_token = db.StringProperty()

    def is_active(self):
        return self.is_enabled and (
            self.is_independent or self.license_state == STATE_ACTIVE)

    def installation_link(self, request):
        if self.installation_token:
            return request.build_absolute_uri(reverse(
                'domain_setup', args=(self.domain,)) + '?token=' +
                self.installation_token)

    @classmethod
    def random_token(cls):
        import hashlib
        import random
        return hashlib.sha1(str(random.random())).hexdigest()[:10]

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


class Role(BaseModel):
    #: Name of the Role.
    name = db.StringProperty(required=True)
    #: List of permissions.
    permissions = db.StringListProperty()

    @classmethod
    def for_domain(cls, domain, **kwargs):
        """Returs a Query object with ``ancestor(domain)`` filter applied."""
        return cls.all(**kwargs).ancestor(domain)


class UserPermissions(BaseModel):
    #: Email address of user.
    user_email = db.EmailProperty(required=True)
    #: List of Roles given user is assigned.
    roles = db.ListProperty(db.Key)
    #: List of permissions given user is assigned.
    permissions = db.StringListProperty()

