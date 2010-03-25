import random
from django import forms
from django.utils.safestring import mark_safe

__all__ = ('TextInput2', 'ExpandField')

def encode_js(text):
    return text.replace('\\', '\\\\').replace('"', '\\"').replace("'", "\\'")

class TextInput2(forms.MultiWidget):
    def __init__(self):
        widgets = (forms.TextInput(), forms.TextInput())
        super(TextInput2, self).__init__(widgets)
    
    def decompress(self, value):
        return value
    
    def format_output(self, rendered_widgets):
        return mark_safe(u' '.join(rendered_widgets))

class ExpandWidget(forms.Widget):
    def __init__(self, widget, collapsed, expanded, *args, **kwargs):
        super(ExpandWidget, self).__init__(*args, **kwargs)
        self.widget = widget
        self.collapsed = collapsed
        self.expanded = expanded
        
        random.seed()
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
