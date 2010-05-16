from django import forms
from django.utils.translation import ugettext as _

from crauth import models
from crgappspanel.helpers import fields, widgets


class DomainForm(forms.Form):
    domain = forms.CharField(label=_('Domain'),
        widget=forms.TextInput(attrs={'class':'long'}))
    admin_email = forms.EmailField(label=_('Admin email'), required=False,
        widget=forms.TextInput(attrs={'class':'long'}))
    admin_password = fields.CharField2(label=_('Admin password'), required=False,
        widget=widgets.DoubleWidget(forms.PasswordInput(), forms.PasswordInput()))
    is_enabled = forms.BooleanField(label=_('Enabled'), required=False)
    is_independent = forms.BooleanField(label=_('Independent'), required=False)
    
    def create(self):
        data = self.cleaned_data
        
        return models.AppsDomain(
            domain=data['domain'],
            admin_email=data['admin_email'],
            admin_password=data['admin_password'][0],
            is_enabled=data['is_enabled'],
            is_independent=data['is_independent'])
    
    def populate(self, domain):
        data = self.cleaned_data
        
        domain.domain = data['domain']
        domain.admin_email = data['admin_email']
        passwords = data['admin_password']
        if passwords and passwords[0] and passwords[0] == passwords[1]:
            domain.admin_password = passwords[0]
        domain.is_enabled = data['is_enabled']
        domain.is_independent = data['is_independent']
    
    def clean_admin_password(self):
        passwords = self.cleaned_data.get('admin_password')
        if passwords and passwords[0] != passwords[1]:
            msg = _('Passwords do not match.')
            raise forms.ValidationError(msg)
        return passwords