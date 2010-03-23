from django.template.loader import render_to_string

class Table(object):
    """Represents table display configuration.
    
    Table consists of:
    - list of visible column specifications
    - id_column - id column specification - provides default sorting order
    - sortby property determining sorting column
    - asc property determining whether sort should be ascending or not
    """
    
    def __init__(self, columns, id_column, sortby=None, asc=None):
        self.columns = columns  # columns presented in the table
        self.id_column = id_column
        
        # setting sort column
        if sortby:
            sortbys = [col for col in self.columns if col.name == sortby]
            if len(sortbys) != 1:
                raise ValueError('Exactly one column must have name equal to sortby name.')
            self.sortby = sortbys[0]
        else:
            self.sortby = self.id_column  # sort by id column by default
        
        # setting sort direction
        self.asc = asc if asc != None else True
    
    def generate(self, objs, widths=None, tableName='table'):
        if widths == None:
            widths = []
        
        rows = []
        for obj in objs:
            rows.append({
                'id': self.id_column.value(obj),
                'data': [col.value(obj) for col in self.columns],
            })
        
        return render_to_string('objects_list.html', {
            'columns': self.columns,
            'rows': rows,
            'sortby': self.sortby,
            'asc': self.asc,
            'widths': widths,
            'tableName': tableName,
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
