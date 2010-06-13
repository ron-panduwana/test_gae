from appengine_django.models import BaseModel
from django.core.urlresolvers import reverse
from google.appengine.ext import db
from google.appengine.api.labs import taskqueue
from crauth import users


class LastCacheUpdate(BaseModel):
    last_updated = db.DateTimeProperty(auto_now=True)


def recache_current_domain():
    domain = users.get_current_domain().domain
    if domain:
        taskqueue.add(url=reverse('precache_domain'), params={'domain': domain})

