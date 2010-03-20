from django.template.loader import render_to_string

class Table(object):
    def __init__(self, columns, sortby=None, asc=None):
        self.columns = columns  # columns presented in the table
        
        self.sortby = columns[0]
        for c in self.columns:
            if sortby == c.name:
                self.sortby = c  # column to sort by
                break
        self.asc = asc          # ascending ?
    
    def generate(self, objs, widths, checkboxName='select'):
        rows = []
        for obj in objs:
            row = []
            for col in self.columns:
                row.append(col.value(obj))
            rows.append(row)
        
        return render_to_string('generic_list.html', {
            'columns': self.columns,
            'rows': rows,
            'sortby': self.sortby,
            'asc': self.asc,
            'widths': widths,
            'checkboxName': checkboxName,
        })
    
    def sort(self, objs):
        objs.sort(key=lambda x: self.sortby.value(x), reverse=not self.asc)

class Column(object):
    def __init__(self, caption, name, getter=None):
        self.caption = caption
        self.name = name
        self.getter = getter
    
    def value(self, obj):
        if self.getter:
            return self.getter(obj)
        if isinstance(obj, dict):
            return obj[self.name]
        else:
            return getattr(obj, self.name)
