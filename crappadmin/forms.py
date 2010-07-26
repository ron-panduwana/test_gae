from django import forms
from django.utils.translation import ugettext_lazy as _

from crauth import models
from crgappspanel.helpers import fields, widgets

#The form being used for creating new domain
class DomainForm(forms.Form):
    """The form being used for creating new domain.

    :param domain: Name of the domain.
    :type domain: CharField
    :param admin_email: Email of domain administrator account.
    :type admin_email: EmailField
    :param admin_password: Password of domain administrator account. 
    :type admin_password: CharField2
    :param is_enabled: Indicates if the domain is enabled. If set to ``False`` the domain will not be able to accees the application.
    :type is_enabled: BooleanField
    :param is_independent: If set to ``True`` the domain is managed manually and Licensing API is not used.
    :type is_independent: BooleanField

    """
	
    domain = forms.CharField(label=_('Domain'),
        widget=forms.TextInput(attrs={'class':'long'}))
    admin_email = forms.EmailField(label=_('Admin email'), required=False,
        widget=forms.TextInput(attrs={'class':'long'}))
    admin_password = fields.CharField2(label=_('Admin password'), required=False,
        widget=widgets.DoubleWidget(forms.PasswordInput(), forms.PasswordInput()))
    is_enabled = forms.BooleanField(label=_('Enabled'), required=False)
    is_independent = forms.BooleanField(label=_('Independent'), required=False)
    
    def create(self):
        """Creates new domain entry, returns object of class class:`AppsDomain`.

        :returns: ``AppsDomain`` object.
        :rtype: AppsDomain

        """
        data = self.cleaned_data
        
        password_list = data['admin_password']
        return models.AppsDomain(
            key_name=data['domain'],
            domain=data['domain'],
            admin_email=data['admin_email'],
            admin_password=password_list and password_list[0] or '',
            is_enabled=data['is_enabled'],
            is_independent=data['is_independent'])
    
    def populate(self, domain):
        """Fills the form, with the given data from a domain.

        :param domain: Google Apps domain.
        :type domain: str

        """
        data = self.cleaned_data
        
        domain.domain = data['domain']
        domain.admin_email = data['admin_email']
        passwords = data['admin_password']
        if passwords and passwords[0] and passwords[0] == passwords[1]:
            domain.admin_password = passwords[0]
        domain.is_enabled = data['is_enabled']
        domain.is_independent = data['is_independent']
    
    def clean_admin_password(self):
        """Returns the admin password and cleans the admin password field.

        :returns: Admin passwords.
        :rtype: array

        """	
        passwords = self.cleaned_data.get('admin_password')
        if passwords and passwords[0] != passwords[1]:
            msg = _('Passwords do not match.')
            raise forms.ValidationError(msg)
        return passwords
