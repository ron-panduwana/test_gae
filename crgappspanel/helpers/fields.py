from django.utils.translation import string_concat, ugettext_lazy as _
from django import forms

from crgappspanel.helpers import widgets

class CharField2(forms.MultiValueField):
    def __init__(self, widget=None, args1=None, args2=None, kwargs1=None, kwargs2=None, *args, **kwargs):
        widget = widget or widgets.DoubleWidget(forms.TextInput(), forms.TextInput())
        field1 = forms.CharField(*(args1 or []), **(kwargs1 or {}))
        field2 = forms.CharField(*(args2 or []), **(kwargs2 or {}))
        super(CharField2, self).__init__((field1, field2), widget=widget, *args, **kwargs)
    
    def compress(self, data_list):
        return data_list


class RegexField2(forms.MultiValueField):
    def __init__(self, widget=None, args1=None, args2=None, kwargs1=None, kwargs2=None, *args, **kwargs):
        widget = widget or widgets.DoubleWidget(forms.TextInput(), forms.TextInput())
        field1 = forms.RegexField(*(args1 or []), **(kwargs1 or {}))
        field2 = forms.RegexField(*(args2 or []), **(kwargs2 or {}))
        super(RegexField2, self).__init__((field1, field2), widget=widget, *args, **kwargs)
    
    def compress(self, data_list):
        return data_list


class RealNameField(forms.MultiValueField):
    REAL_NAME_CHOICES = (
        (u'-', u''),
        (u'mr', _('Mr.')),
        (u'mrs', _('Mrs.')),
        (u'miss', _('Miss')),
        (u'ms', _('Ms.'))
    )

    def __init__(self, *args, **kwargs):
        widget = widgets.DoubleWidget(
            forms.TextInput(), forms.TextInput())
        fields = tuple(forms.CharField() for x in xrange(2))
        super(RealNameField, self).__init__(fields, widget=widget, *args, **kwargs)
    
    def compress(self, data_list):
        return data_list


class PermissionsField(forms.MultiValueField):
    def __init__(self, *args, **kwargs):
        widget = widgets.TripleWidget(forms.CheckboxInput(),
            forms.CheckboxInput(), forms.CheckboxInput())
        fields = tuple(forms.BooleanField() for x in xrange(3))
        super(PermissionsField, self).__init__(fields, widget=widget, *args, **kwargs)
    
    def compress(self, data_list):
        res = []
        if data_list[0]:
            res.append('add')
        if data_list[1]:
            res.append('change')
        if data_list[2]:
            res.append('read')
        return res
