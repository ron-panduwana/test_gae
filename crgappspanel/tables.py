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
        def compare(x, y):
            xx = x[self.sortby]
            yy = y[self.sortby]
            if xx < yy:
                if self.asc:
                    return -1
                else:
                    return 1
            elif xx > yy:
                if self.asc:
                    return 1
                else:
                    return -1
            else:
                return 0
        
        objs.sort(compare)

class Field(object):
    def __init__(self, name, caption):
        self.name = name
        self.caption = caption
