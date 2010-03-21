from django.template.loader import render_to_string

class Table(object):
    def __init__(self, columns, sortby=None, asc=None):
        self.columns = columns  # columns presented in the table
        self.id_column = None
        
        # looking for id column
        for col in self.columns:
            if col.id:
                if self.id_column != None:
                    raise ValueError('Exactly one column must have id=True')
                self.id_column = col  # id column found
        if self.id_column == None:
            raise ValueError('Exactly one column must have id=True')
        
        # setting sort properties
        self.sortby = self.id_column  # sort by id column by default
        for col in self.columns:
            if sortby == col.name:
                self.sortby = col  # column to sort by
                break
        self.asc = asc          # ascending ?
    
    def generate(self, objs, widths, checkboxName='select'):
        rows = []
        for obj in objs:
            row = {
                'id': self.id_column.value(obj),
                'data': [],
            }
            for col in self.columns:
                row['data'].append(col.value(obj))
            rows.append(row)
        
        return render_to_string('objects_list.html', {
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
    def __init__(self, caption, name, getter=None, id=False):
        self.caption = caption
        self.name = name
        self.getter = getter
        self.id = id
    
    def value(self, obj):
        if self.getter:
            return self.getter(obj)
        if isinstance(obj, dict):
            return obj[self.name]
        else:
            return getattr(obj, self.name)
