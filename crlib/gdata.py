from google.appengine.ext import db


class GDataQuery(object):
    def __init__(self, model_class):
        self._filters = []
        self._model = model_class

    def filter(self, property_operator, value):
        raise NotImplemented

    def get(self):
        results = self.fetch(1)
        if results:
            return results[0]

    def fetch(self, limit, offset=0):
        items = []
        for i, item in enumerate(self._model.gdata_retrieve_all()):
            if i < limit:
                items.append(self._model._from_atom(item))
        return items


class StringProperty(db.Property):
    def __init__(self, attr, *args, **kwargs):
        self.attrs = attr.split('.')
        self.read_only = kwargs.pop('read_only', False)
        super(StringProperty, self).__init__(*args, **kwargs)

    def make_value_from_atom(self, atom):
        for attr in self.attrs:
            atom = getattr(atom, attr)
        return atom

    def set_value_on_atom(self, atom, value):
        if self.read_only:
            return
        for attr in self.attrs[:-1]:
            atom = getattr(atom, attr)
        setattr(atom, self.attrs[-1], value)


class BooleanProperty(StringProperty):
    def make_value_from_atom(self, atom):
        return super(
            BooleanProperty, self).make_value_from_atom(atom) == 'true'

    def set_value_on_atom(self, atom, value):
        super(BooleanProperty, self).set_value_on_atom(
            atom, value and 'true' or 'false')


class IntegerProperty(StringProperty):
    def make_value_from_atom(self, atom):
        return int(super(IntegerProperty, self).make_value_from_atom(atom))

    def set_value_on_atom(self, atom, value):
        super(IntegerProperty, self).set_value_on_atom(atom, str(value))


# TODO: ReferenceProperty, ListProperty


class _GDataService(object):
    def __init__(self, service):
        from lib.gdata.alt.appengine import run_on_appengine
        run_on_appengine(service)
        self.service = service
        self.logged_in = False

    def __get__(self, instance, owner):
        if not self.logged_in:
            self.service.ProgrammaticLogin()
            self.logged_in = True
        return self.service


class _GDataModelMetaclass(db.PropertiedClass):
    def __new__(cls, name, bases, attrs):
        new_cls = super(_GDataModelMetaclass, cls).__new__(cls, name, bases, attrs)
        if name == 'Model':
            return new_cls

        new_cls.service = _GDataService(new_cls.gdata_service())
        del new_cls.gdata_service

        return new_cls


class Model(object):
    __metaclass__ = _GDataModelMetaclass

    def __init__(self, **kwargs):
        self._atom = kwargs.pop('_atom', None)

        for prop in self._properties.values():
            if prop.name in kwargs:
                value = kwargs[prop.name]
            else:
                value = prop.default_value()
            prop.__set__(self, value)

    @classmethod
    def all(cls):
        return GDataQuery(cls)

    def save(self):
        if self._atom:
            for prop in self._properties.values():
                prop.set_value_on_atom(self._atom, getattr(self, prop.name))
            self.gdata_update(self._atom)
        else:
            self._atom = self.gdata_create()
    put = save

    @classmethod
    def kind(cls):
        return cls.__name__

    @classmethod
    def get_by_key_name(cls, key_name):
        try:
            atom = cls.gdata_retrieve(key_name)
        except Exception, e:
            return None
        return cls._from_atom(atom)

    @classmethod
    def _from_atom(cls, atom):
        props = {'_atom' : atom}
        for prop in cls._properties.values():
            props[prop.name] = prop.make_value_from_atom(atom)
        return cls(**props)


