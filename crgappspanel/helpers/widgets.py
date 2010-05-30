import random
from django import forms
from django.utils.safestring import mark_safe

__all__ = ('DoubleWidget', 'TripleWidget', 'SwapWidget')

def encode_js(text):
    return text.replace('\\', '\\\\').replace('"', '\\"').replace("'", "\\'")


class DoubleWidget(forms.MultiWidget):
    join_with = u' '
    
    def __init__(self, widget1, widget2):
        widgets = (widget1, widget2)
        super(DoubleWidget, self).__init__(widgets)
    
    def decompress(self, value):
        if value is None:
            return [None, None]
        return value
    
    def format_output(self, rendered_widgets):
        return mark_safe(self.join_with.join(rendered_widgets))


class TripleWidget(forms.MultiWidget):
    join_with = u' '
    
    def __init__(self, widget1, widget2, widget3):
        widgets = (widget1, widget2, widget3)
        super(TripleWidget, self).__init__(widgets)
    
    def decompress(self, value):
        if value is None:
            return [None, None, None]
        return value
    
    def format_output(self, rendered_widgets):
        return mark_safe(self.join_with.join(rendered_widgets))


class SwapWidget(forms.Widget):
    def __init__(self, text_c, widget, text_e, *args, **kwargs):
        super(SwapWidget, self).__init__(*args, **kwargs)
        self.text_c = text_c
        self.widget = widget
        self.text_e = text_e
        
        id = ''
        for i in xrange(25):
            id += chr(random.randint(ord('a'), ord('z')))
        self.id = id
    
    def render(self, name, value, attrs=None):
        d = {
            'link_start': '''<a href="#" onclick="cr.swapWidget.swap('%s')">''' % self.id,
            'link_end': '</a>',
        }
        
        ctx = {
            'id': self.id,
            'content_c': self.text_c % d,
            'content_e': self.text_e % dict(d, widget=self.widget.render(name, value)),
        }
        
        return mark_safe(u'''
            <div id="swapWidget_%(id)s_c" style="margin: 0; padding: 0; display: block">
                %(content_c)s
            </div>
            <div id="swapWidget_%(id)s_e" style="margin: 0; padding: 0; display: none">
                %(content_e)s
            </div>
            ''' % ctx)
