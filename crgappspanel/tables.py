class Table(object):
    def __init__(self, fields, sortby=None, asc=None):
        self.fields = fields  # fields presented in the table
        self.sortby = sortby  # field to sort by
        self.asc = asc        # ascending ?
    
    def generate(self, objs):
        columns = [f for f in self.fields]
        
        rows = []
        for obj in objs:
            row = []
            for field in self.fields:
                row.append(obj[field.name])
            rows.append(row)
        
        return {
            'columns': columns,
            'rows': rows,
            'sortby': self.sortby,
            'asc': self.asc,
        }
    
    def sort(self, objs):
        objs.sort(key=lambda x: x[self.sortby], reverse=not self.asc)

class Field(object):
    def __init__(self, name, caption):
        self.name = name
        self.caption = caption
