class Table(object):
    def __init__(self, fields):
        self.fields = fields  # fields presented in the table
    
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
            'rows': rows
        }

class Field(object):
    def __init__(self, name, caption):
        self.name = name
        self.caption = caption
