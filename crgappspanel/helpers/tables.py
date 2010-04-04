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
        # checking column name uniqueness
        if len(columns) != len(set(col.name for col in columns)):
            raise ValueError('Column names are not unique')
        
        self.columns = columns  # columns presented in the table
        self.id_column = id_column
        
        # setting sort column
        if sortby:
            sortbys = [col for col in self.columns if col.name == sortby]
            if sortbys:
                self.sortby = sortbys[0]
            else:
                self.sortby = self.id_column  # sort by id column if sortby is not valid
        else:
            self.sortby = self.id_column  # sort by id column by default
        
        # setting sort direction
        self.asc = asc if asc != None else True
    
    def generate(self, objs, widths=None, table_name='table', singular='object', plural=None):
        if widths == None:
            widths = []
        
        rows = []
        for obj in objs:
            rows.append({
                'id': self.id_column.value(obj),
                'data': [col.value(obj) for col in self.columns],
            })
        
        plural = plural or ('%ss' % singular)
        
        return render_to_string('objects_list.html', {
            'columns': self.columns,
            'rows': rows,
            'sortby': self.sortby,
            'asc': self.asc,
            'widths': widths,
            'table_name': table_name,
            'object_singular': singular,
            'object_plural': plural,
        })
    
    def sort(self, objs):
        def key(x):
            value = self.sortby.value(x)
            if isinstance(value, str):
                value = str.lower(self.sortby.value(x))
            return value
        objs.sort(key=key, reverse=not self.asc)


class Column(object):
    def __init__(self, caption, name, getter=None, default=None):
        self.caption = caption
        self.name = name
        self.getter = getter
        self.default = default
    
    def value(self, obj):
        if self.getter:
            value = self.getter(obj)
        elif isinstance(obj, dict):
            value = obj[self.name]
        else:
            value = getattr(obj, self.name)
        return value if value is not None else self.default