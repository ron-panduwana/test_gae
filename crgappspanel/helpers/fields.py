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


class RealNameField(forms.MultiValueField):
    def __init__(self, *args, **kwargs):
        choices = ((u'-', u''), (u'mr', u'Mr.'), (u'mrs', u'Mrs.'), (u'miss', 'Miss'), (u'ms', u'Ms.'))
        widget = widgets.TripleWidget(forms.Select(None, choices), forms.TextInput(), forms.TextInput())
        fields = tuple(forms.CharField() for x in xrange(3))
        super(RealNameField, self).__init__(fields, widget=widget, *args, **kwargs)
    
    def compress(self, data_list):
        return data_list
