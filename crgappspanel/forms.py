from django import forms

from crgappspanel.helpers import fields, widgets

__all__ = ('UserForm', 'LoginForm')

class UserForm(forms.Form):
    user_name = forms.CharField(label='User name')
    full_name = fields.CharField2(label='Full name')
    admin = forms.BooleanField(label='Privileges', required=False, help_text='Administrators can manage all users and settings for this domain')
    nicknames = forms.CharField(label='Nicknames', required=False, widget=widgets.ExpandWidget(forms.TextInput(), '%(link_start)sAdd nickname%(link_end)s', 'Enter nickname:<br/>%(widget_html)s %(link_start)sCancel%(link_end)s'))
    
    def populate(self, user):
        user.user_name = self.cleaned_data['user_name']
        user.given_name = self.cleaned_data['full_name'][0]
        user.family_name = self.cleaned_data['full_name'][1]
        user.admin = self.cleaned_data['admin']
    
    def get_nickname(self):
        nicknames = self.cleaned_data['nicknames'].strip()
        if nicknames:
            return nicknames
        return None

