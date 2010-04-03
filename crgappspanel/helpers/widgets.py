import random
from django import forms
from django.utils.safestring import mark_safe

__all__ = ('TextInput2', 'ExpandWidget', 'SwapWidget')

def encode_js(text):
    return text.replace('\\', '\\\\').replace('"', '\\"').replace("'", "\\'")

class DoubleWidget(forms.MultiWidget):
    def __init__(self, widget1, widget2):
        widgets = (widget1, widget2)
        super(DoubleWidget, self).__init__(widgets)
    
    def decompress(self, value):
        if value is None:
            return [None, None]
        return value
    
    def format_output(self, rendered_widgets):
        return mark_safe(u' '.join(rendered_widgets))

class ExpandWidget(forms.Widget):
    def __init__(self, widget, collapsed, expanded, *args, **kwargs):
        super(ExpandWidget, self).__init__(*args, **kwargs)
        self.widget = widget
        self.collapsed = collapsed
        self.expanded = expanded
        
        id = ''
        for i in xrange(25):
            id += chr(random.randint(ord('a'), ord('z')))
        self.id = id
    
    def render(self, name, value, attrs=None):
        links_dict = {
            'link_start': '''<a href="#" onclick="cr.expandField.toggleExpandField('%s')">''' % self.id,
            'link_end': '</a>',
            'widget_html': self.widget.render(name, value),
        }
        
        ctx = {
            'id': self.id,
            'hidden_html': forms.HiddenInput().render(name, value),
            'content': self.collapsed % links_dict,
            'expanded_js': encode_js(self.expanded % links_dict),
        }
        
        return mark_safe(u'''
            <script type="text/javascript">
                cr.expandField.expandFields['%(id)s'] = '%(expanded_js)s'
            </script>
            <div id="expandField_%(id)s" style="margin: 0; padding: 0">
                %(hidden_html)s
                %(content)s
            </div>''' % ctx)

class SwapWidget(forms.Widget):
    def __init__(self, widget_c, text_c, widget_e, text_e, *args, **kwargs):
        super(SwapWidget, self).__init__(*args, **kwargs)
        self.widget_c = widget_c
        self.text_c = text_c
        self.widget_e = widget_e
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
            'content_c': self.text_c % dict(d, widget=self.widget_c.render(name, value)),
            'content_e': self.text_e % dict(d, widget=self.widget_e.render(name, value)),
        }
        
        return mark_safe(u'''
            <div id="swapWidget_%(id)s_c" style="margin: 0; padding: 0; display: block">
                %(content_c)s
            </div>
            <div id="swapWidget_%(id)s_e" style="margin: 0; padding: 0; display: none">
                %(content_e)s
            </div>
            ''' % ctx)
