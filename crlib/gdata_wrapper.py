from google.appengine.ext import db
from google.appengine.api import memcache
from atom import AtomBase
from atom.token_store import TokenStore


BadValueError = db.BadValueError


def _clone_atom(atom):
    """Make a copy of atom object."""
    from lib.atom import CreateClassFromXMLString
    return CreateClassFromXMLString(atom.__class__, unicode(atom))


class GDataQuery(object):
    """db.Query equivalent."""
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
        """Fetch given number of elements from a feed provided by
        AtomMapper.retrieve_all().

        """
        items = []
        for i, item in enumerate(self._model._mapper.retrieve_all()):
            if i < limit:
                items.append(self._model._from_atom(item))
        return items


class StringProperty(db.Property):
    """This and below classes are equivalents of respective db.Property classes.

    Go to .google_appengine/google/appengine/ext/db/ for original
    implementation.

    Design of these classes resembles db.Property. Whereas db.Property has
    get_value_for_datastore() and make_value_from_datastore() to convert between
    datastore representation and Python native objects, we use
    make_value_from_atom() and set_value_on_atom().

    We use the same constructor parameters as db.Property (i.e. required,
    default, etc), but we also add new parameter: read_only, which says that the
    property shouldn't be persisted to GData.

    The first parameter to property constructor is attribute name within Atom
    object that holds respective value. For example, given gdata.apps.UserEntry
    object attribute name 'login.user_name' would correspond to:

    user_entry.login.user_name

    """

    def __init__(self, attr, *args, **kwargs):
        self.attrs = attr.split('.')
        self.read_only = kwargs.pop('read_only', False)
        super(StringProperty, self).__init__(*args, **kwargs)

    def make_value_from_atom(self, atom):
        """Given a subclass of atom.AtomBase return corresponding value for this
        property.
        """
        for attr in self.attrs:
            atom = getattr(atom, attr)
        return atom

    def set_value_on_atom(self, atom, value):
        """Set the property value at the given place within the atom object.

        """
        if self.read_only:
            return
        for attr in self.attrs[:-1]:
            atom = getattr(atom, attr)
        setattr(atom, self.attrs[-1], value)


class PasswordProperty(StringProperty):
    """Hashes given property with SHA-1."""
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
    """Equivalent of db.ReferenceProperty.

    Most of the code is actually copied from Google original implementation.
    Unfortunately, it's not so easy to simply subclass db.ReferenceProperty,
    because there are minor but important differences (db.ReferenceProperty uses
    db.Key as a intermediate representation whereas we simply use a string.

    """
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
    """This class is an atom.AtomBase replacement which allows for simple
    attribute assignments, e.g.:

    mt = EmptyAtom()
    mt.attr1.attr2 = 'val'
    mt.attr3 = 5

    print mt.attr1 => EmptyAtom object
    print mt.attr1.attr2 => 'val'

    """
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
    """db.BaseModel (and usual Django model) replacement.

    This class provides most of the db.BaseModel methods, i.e. all(),
    get_by_key_name(), put(), etc.
    It of course doesn't interact with App Engine datastore, but instead uses
    Python GData bindings.
    It needs additional object - AtomMapper, which provides actual
    implementation of GData interaction. This mapper is declared as Mapper class
    attribute, and then it's available as _mapper attribute.

    Usual model methods are mapped to mapper methods in the following way:

        save()/put() -> _mapper.update() or _mapper.create() (depending on
            whether it's first save of the object);
        all() -> _mapper.retrieve_all();
        get_by_key_name() -> _mapper.retrieve();

    Mapper methods work on AtomBase subclasses, which are stored in Model's
    _atom attribute. This attribute is updated after save() call (so that it
    stores a value which would be returned from GData API).

    """

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
        """Returns a dictionary of property values read from the AtomBase
        object, e.g.:

            {'user_name': value of atom.login.user_name}

        """
        props = {}
        for prop in cls._properties.values():
            props[prop.name] = prop.make_value_from_atom(atom)
        return props

    @classmethod
    def _from_atom(cls, atom):
        """Creates new Model instance from given AtomBase object."""
        props = {'_atom' : atom}
        props.update(cls._atom_to_kwargs(atom))
        return cls(**props)


class GDataCaptchaRequiredError(Exception):
    def __init__(self, domain):
        self.domain = domain


class _GDataServiceDescriptor(object):
    """This object makes sure that ProgrammaticLogin() is called before the
    gdata.GDataService objects is used for the first time and it makes sure that
    it's called only once.

    It's a Python descriptor:

    http://docs.python.org/reference/datamodel.html#implementing-descriptors

    """
    MEMCACHE_KEY = 'clientlogintoken:%s'
    DAY = 24 * 60 * 60

    def __get__(self, instance, owner):
        if instance._service.GetClientLoginToken() is None:
            # Try to get the token from memcache
            key = self.MEMCACHE_KEY % instance._service.email
            token = memcache.get(key)
            if token:
                instance._service.SetClientLoginToken(token)
            else:
                # ProgrammaticLogin may raise CaptchaRequired:
                # We handle this situation in
                # crgappspanel.middleware.CaptchaRequiredMiddleware:
                # http://code.google.com/intl/pl/googleapps/faq.html#captchas
                from gdata.service import CaptchaRequired
                try:
                    instance._service.ProgrammaticLogin()
                    # The auth token is valid for 24 hours:
                    # http://code.google.com/intl/pl/googleapps/faq.html#avoidcaptcha
                    # We keep it 30 minutes shorter than that to avoid using
                    # invalid token
                    memcache.set(key, instance._service.GetClientLoginToken(),
                                 self.DAY - 30 * 60)
                except CaptchaRequired:
                    raise GDataCaptchaRequiredError(instance._service.domain)
        return instance._service


class AtomMapper(object):
    """Subclasses of this class implement actual interaction with GData APIs.

    AtomMapper corresponds to AtomBase subclass (e.g. UserEntry, NicknameEntry,
    etc.).
    It should provide the following methods:

    create_service() -> return proper gdata.service.GDataService object;
    create() -> called when new Model instance is to be saved for the first
        time;
    update() -> called when Model instance is to be saved after initial
        create();
    retrieve_all() -> returns all instances of the given Atom object, used by
        GDataQuery.fetch();
    retrieve() -> used to retrieve Model instance by its key_name, i.e. it's
        called by Model.get_by_key_name().

    """

    token_store = TokenStore()
    service = _GDataServiceDescriptor()

    def __init__(self, *args, **kwargs):
        self._service = self.create_service(*args, **kwargs)


class UserEntryMapper(AtomMapper):
    @classmethod
    def create_service(cls, email, password, domain):
        from gdata.apps import service
        from gdata.alt.appengine import run_on_appengine
        service = service.AppsService(email, password, domain,
                                      token_store=cls.token_store)
        return service


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

