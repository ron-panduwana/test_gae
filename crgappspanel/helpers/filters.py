__all__ = ('NullFilter', 'AnyAttributeFilter', 'AllAttributeFilter')

class NullFilter(object):
    
    def match(self, obj):
        return True
    
    def __repr__(self):
        return 'NullFilter()'
    
    def __unicode__(self):
        return 'filter:true'


class AttributeFilter(object):
    def __init__(self, query):
        self.query = query
    
    @staticmethod
    def get_values(obj, attr):
        # attribute is None
        if attr is None:
            if isinstance(obj, (list, tuple)):
                return list(obj)
            else:
                return [str(obj)]
        
        # object is None
        if obj is None:
            return []
        
        # checking if attribute is composite attribute
        idx = attr.find('.')
        if idx != -1:
            rest = attr[idx+1:]
            attr = attr[:idx]
        else:
            rest = None
        
        try:
            obj = getattr(obj, attr)
            if obj is None:
                return []
            
            res = []
            if isinstance(obj, (list, tuple)):
                for x in obj:
                    res.extend(AttributeFilter.get_values(x, rest))
            else:
                res.extend(AttributeFilter.get_values(obj, rest))
            return res
        except:
            return []
    
    def __repr__(self):
        return 'AttributeFilter([%s], %s)' % (', '.join(self.attrs), self.query)
    
    def __unicode__(self):
        return 'filter[%s]:%s' % (','.join(self.attrs), self.query)


class AnyAttributeFilter(AttributeFilter):
    def match(self, obj):
        for key, value in self.query.iteritems():
            values = AttributeFilter.get_values(obj, key)
            ok = any(value.lower() in v.lower() for v in values)
            if ok:
                return True
        return False


class AllAttributeFilter(AttributeFilter):
    def match(self, obj):
        for key, value in self.query.iteritems():
            values = AttributeFilter.get_values(obj, key)
            ok = any(value.lower() in v.lower() for v in values)
            if not ok:
                return False
        return True


class SharedContactFilter(AttributeFilter):
    def __init__(self, full_name=None, notes=None, email=None):
        super(ArrtibuteFilter, self).__init__()
    
    def match(self, obj):
        res = []
        if obj.name is not None:
            res.append(obj.name.full_name)
        res.append(obj.notes)
        for email in obj.emails:
            res.append(email.address)
        
        return any(str(x).find(self.query) != -1 for x in res)
    
    def __repr__(self):
        return 'SharedContactFilter(%s)' % self.query
    
    def __unicode__(self):
        return 'filter:query:%s' % self.query
                