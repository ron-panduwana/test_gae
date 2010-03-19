class Table(object):
    def __init__(self, fields, widths, select=False, sortby='', asc=True, html_width=None, css_class=None):
        self.fields = fields          # fields presented in the table
        self.widths = widths          # table column widths
        self.select = select          # selection column
        self.sortby = sortby          # field to sort by
        self.asc = asc                # ascending?
        self.html_width = html_width  # html width attribute
        self.css_class = css_class    # table css classes
    
    def gen_js(self, objs):
        return ''
    
    def gen_html(self, objs):
        # starting with table start tag with appropriate class
        s = '<table'
        if self.html_width:
            s += ' width="%s"' % self.html_width
        if self.css_class:
            s += ' class="%s"' % self.css_class
        s += '>'
        
        # adding column width specifiers
        for width in self.widths:
            s += '<col width="%s"/>' % str(width)
        
        # generating table head
        s += '<thead><tr>'
        if self.select:
            s += '<th><input type="checkbox"/></th>'
        for field in self.fields:
            s += '<th><a'
            if field.name == self.sortby:
                if self.asc:
                    s += ' class="asc" href="?sortby=%s&asc=false">' % field.name
                else:
                    s += ' class="desc" href="?sortby=%s">' % field.name
            else:
                s += ' href="?sortby=%s">' % field.name
            s += '%s</a></th>' % field.caption
        s += '</tr></thead>'
        
        # generating table body
        s += '<tbody>'
        for obj in objs:
            s += '<tr>'
            if self.select:
                s += '<td><input type="checkbox"/></td>'
            for field in self.fields:
                s += '<td>%s</td>' % str(obj[field.name])
            s += '</tr>'
        s += '</tbody>'
        
        # closing table tag
        s += '</table>'
        
        return s

class Field(object):
    def __init__(self, name, caption):
        self.name = name
        self.caption = caption
