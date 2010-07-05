import datetime
from django import forms
from django.utils.translation import ugettext as _

from crauth import models
from crgappspanel.helpers import fields, widgets

#The form being used for creating new domain
class DomainForm(forms.ModelForm):
    """The form being used for creating new domain.

    """
    class Meta:
        model = models.AppsDomain
        fields = (
            'domain', 'admin_email', 'admin_password',
            'is_enabled', 'is_independent', 'is_on_trial',
            'expiration_date',
        )

    def clean_admin_password(self):
        password = self.cleaned_data['admin_password']
        return password or self.instance.admin_password

    def clean_expiration_date(self):
        date = self.cleaned_data['expiration_date']
        return date or datetime.date.max

