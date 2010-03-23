from django.template.loader import render_to_string

class Table(object):
    def __init__(self, columns, sortby=None, asc=None):
        self.columns = columns  # columns presented in the table
        self.id_column = None
        
        # looking for id column
        ids = [col for col in self.columns if col.id]
        if len(ids) != 1:
            raise ValueError('Exactly one column must have id=True.')
        self.id_column = ids[0]
        
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
    
    def generate(self, objs, widths, tableName='table'):
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
