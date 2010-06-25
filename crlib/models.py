from appengine_django.models import BaseModel
from google.appengine.ext import db


class LastCacheUpdate(BaseModel):
    last_updated = db.DateTimeProperty(auto_now=True)

