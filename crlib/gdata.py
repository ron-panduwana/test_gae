from google.appengine.ext import db
from lib.atom import AtomBase


BadValueError = db.BadValueError


def _clone_atom(atom):
    from lib.atom import CreateClassFromXMLString
    return CreateClassFromXMLString(atom.__class__, unicode(atom))


class GDataQuery(object):
    def __init__(self, model_class):
        self._filters = []
        self._model = model_class

    def filter(self, property_operator, value):
        raise NotImplementedError

    def get(self):
        results = self.fetch(1)
        if results:
            return results[0]

    def fetch(self, limit, offset=0):
        items = []
        for i, item in enumerate(self._model._mapper.retrieve_all()):
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


class PasswordProperty(StringProperty):
    def set_value_on_atom(self, atom, value):
        if not value:
            return
        import hashlib
        hashed = hashlib.sha1(unicode(value).encode('utf8')).hexdigest()
        super(PasswordProperty, self).set_value_on_atom(atom, hashed)


class BooleanProperty(StringProperty):
    def make_value_from_atom(self, atom):
        return super(
            BooleanProperty, self).make_value_from_atom(atom) == 'true'

    def set_value_on_atom(self, atom, value):
        super(BooleanProperty, self).set_value_on_atom(
            atom, value and 'true' or 'false')

    def validate(self, value):
        value = super(BooleanProperty, self).validate(value)
        if value is not None and not isinstance(value, bool):
            raise BadValueError('Property %s must be a bool' % self.name)
        return value


class IntegerProperty(StringProperty):
    def make_value_from_atom(self, atom):
        return int(super(IntegerProperty, self).make_value_from_atom(atom))

    def set_value_on_atom(self, atom, value):
        super(IntegerProperty, self).set_value_on_atom(atom, str(value))


class ReferenceProperty(StringProperty):
    def __init__(self, reference_class, *args, **kwargs):
        self.reference_class = reference_class
        self.collection_name = kwargs.pop('collection_name', None)
        super(ReferenceProperty, self).__init__(*args, **kwargs)

    def __property_config__(self, model_class, property_name):
        super(ReferenceProperty, self).__property_config__(
            model_class, property_name)

        if self.collection_name is None:
            self.collection_name = '%s_set' % (model_class.__name__.lower())

        setattr(
            self.reference_class, self.collection_name,
            _ReverseReferenceProperty(model_class, property_name))

    def set_value_on_atom(self, atom, value):
        super(ReferenceProperty, self).set_value_on_atom(
            atom, value.key())

    def __get__(self, model_instance, model_class):
        """Get reference object.

        This method will fetch unresolved entities from the datastore if
        they are not already loaded.

        Returns:
          ReferenceProperty to Model object if property is set, else None.
        """
        if model_instance is None:
            return self
        if hasattr(model_instance, self.__id_attr_name()):
            reference_id = getattr(model_instance, self.__id_attr_name())
        else:
            reference_id = None
        if reference_id is not None:
            resolved = getattr(model_instance, self.__resolved_attr_name())
            if resolved is not None:
                return resolved
            else:
                instance = self.reference_class.get_by_key_name(reference_id)
                if instance is None:
                    raise Error('ReferenceProperty failed to be resolved')
                setattr(model_instance, self.__resolved_attr_name(), instance)
                return instance
        else:
            return None

    def __set__(self, model_instance, value):
        """Set reference."""
        value = self.validate(value)
        if value is not None:
            if isinstance(value, basestring):
                setattr(model_instance, self.__id_attr_name(), value)
                setattr(model_instance, self.__resolved_attr_name(), None)
            else:
                setattr(model_instance, self.__id_attr_name(), value.key())
                setattr(model_instance, self.__resolved_attr_name(), value)
        else:
            setattr(model_instance, self.__id_attr_name(), None)
            setattr(model_instance, self.__resolved_attr_name(), None)

    def __id_attr_name(self):
        """Get attribute of referenced id.

        Returns:
          Attribute where to store id of referenced entity.
        """
        return self._attr_name()

    def __resolved_attr_name(self):
        """Get attribute of resolved attribute.

        The resolved attribute is where the actual loaded reference instance is
        stored on the referring model instance.

        Returns:
          Attribute name of where to store resolved reference model instance.
        """
        return '_RESOLVED' + self._attr_name()


class _ReverseReferenceProperty(db._ReverseReferenceProperty):
    def __get__(self, model_instance, model_class):
        """Fetches collection of model instances of this collection property."""
        if model_instance is not None:
            query = GDataQuery(self.__model)
            return query.filter(self.__property + ' =', model_instance.key())
        else:
            return self


# TODO: ListProperty


class _GDataModelMetaclass(db.PropertiedClass):
    def __new__(cls, name, bases, attrs):
        new_cls = super(_GDataModelMetaclass, cls).__new__(cls, name, bases, attrs)
        if name == 'Model':
            return new_cls

        new_cls._mapper = new_cls.Mapper
        del new_cls.Mapper

        return new_cls


class EmptyAtom(object):
    def __init__(self):
        self._attrs = {}

    def __setattr__(self, name, value):
        if name.startswith('_'):
            self.__dict__[name] = value
        else:
            self.__dict__['_attrs'][name] = value

    def __getattr__(self, name):
        if not self.__dict__['_attrs'].has_key(name):
            setattr(self, name, EmptyAtom())
        return self.__dict__['_attrs'][name]


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
        atom = self._atom and _clone_atom(self._atom) or EmptyAtom()
        for prop in self._properties.itervalues():
            prop.set_value_on_atom(atom, getattr(self, prop.name))
        if self.is_saved():
            if not hasattr(self._mapper, 'update'):
                raise Exception('Mapper %s doesn\'t support model updates.' %
                                self._mapper)
            self._atom = self._mapper.update(atom, self._atom)
        else:
            self._atom = self._mapper.create(atom)
    put = save

    def is_saved(self):
        return self._atom is not None

    @classmethod
    def kind(cls):
        return cls.__name__

    @classmethod
    def get_by_key_name(cls, key_name):
        try:
            atom = cls._mapper.retrieve(key_name)
        except Exception, e:
            return None
        return cls._from_atom(atom)

    @classmethod
    def _atom_to_kwargs(cls, atom):
        props = {}
        for prop in cls._properties.values():
            props[prop.name] = prop.make_value_from_atom(atom)
        return props

    @classmethod
    def _from_atom(cls, atom):
        props = {'_atom' : atom}
        props.update(cls._atom_to_kwargs(atom))
        return cls(**props)


class _GDataServiceDescriptor(object):
    def __get__(self, instance, owner):
        if instance._service.GetClientLoginToken() is None:
            instance._service.ProgrammaticLogin()
        return instance._service


class AtomMapper(object):
    from atom.token_store import TokenStore
    token_store = TokenStore()
    service = _GDataServiceDescriptor()

    def __init__(self, *args, **kwargs):
        self._service = self.create_service(*args, **kwargs)


class UserEntryMapper(AtomMapper):
    @classmethod
    def create_service(cls, email, password, domain):
        from lib.gdata.apps import service
        return service.AppsService(
            email, password, domain, token_store=cls.token_store)

    def create(self, atom):
        return self.service.CreateUser(
            atom.login.user_name, atom.name.family_name,
            atom.name.given_name, atom.login.password,
            atom.login.suspended, password_hash_function='SHA-1')

    def update(self, atom, old_atom):
        atom.login.hash_function_name = 'SHA-1'
        return self.service.UpdateUser(old_atom.login.user_name, atom)

    def retrieve_all(self):
        return self.service.RetrieveAllUsers().entry

    def retrieve(self, user_name):
        return self.service.RetrieveUser(user_name)


class NicknameEntryMapper(AtomMapper):
    create_service = UserEntryMapper.create_service

    def create(self, atom):
        return self.service.CreateNickname(
            atom.login.user_name, atom.nickname.name)

    def retrieve_all(self):
        return self.service.RetrieveAllNicknames().entry

    def retrieve(self, nickname):
        return self.service.RetrieveNickname(nickname)

    #@filter('user')
    #def filter_by_user(self, user_name):
    #    return self.service.RetrieveNicknames(user_name).entry

