from django import forms


class UserForm(forms.Form):
    user_name = forms.CharField(widget=forms.TextInput(attrs={'disabled': 'disabled'}))
    given_name = forms.CharField(label='Given name')
    family_name = forms.CharField(label='Family name')
    admin = forms.BooleanField(label='Privileges', required=False, help_text='Administrators can manage all users and settings for this domain')
