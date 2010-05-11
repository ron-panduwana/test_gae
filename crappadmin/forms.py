from django import forms
from django.utils.translation import ugettext as _

from crauth import licensing
from crgappspanel.helpers import fields, widgets


LICENSE_STATES = [(state, _(state)) for state in licensing.LICENSE_STATES]


class DomainForm(forms.Form):
    domain = forms.CharField(label=_('Domain'))
    admin_email = forms.EmailField(label=_('Admin email'), required=False)
    admin_password = fields.CharField2(label=_('Admin password'), required=False,
        widget=widgets.DoubleWidget(forms.PasswordInput(), forms.PasswordInput()))
    license_state = forms.ChoiceField(label=_('License'),
        choices=LICENSE_STATES)
    is_enabled = forms.BooleanField(label=_('Enabled'), required=False)
    is_independent = forms.BooleanField(label=_('Independent'), required=False)
