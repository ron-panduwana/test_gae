import logging
import operator
import re
from google.appengine.ext import db
from google.appengine.api import memcache
from atom import AtomBase
from atom.token_store import TokenStore
from django.conf import settings


BadValueError = db.BadValueError


def _clone_atom(atom):
    """Make a copy of atom object."""
    from lib.atom import CreateClassFromXMLString
    return CreateClassFromXMLString(atom.__class__, unicode(atom))


class GDataQuery(object):
    """db.Query equivalent."""

    _PROPERTY_RE = re.compile(r'([\w_]+)\s*(\<|\<\=|\=|\>\=|\>|\!\=|[iI][nN])?\s*$')
    _FUNCS = {
        '>': operator.gt,
        '>=': operator.ge,
        '<': operator.lt,
        '<=': operator.le,
        '!=': operator.ne,
        '=': operator.eq,
        'in': lambda *args: False,
    }

    def __init__(self, model_class):
        self._filters = []
        self._orders = []
        self._model = model_class

    def order(self, property):
        self._orders.append((
            property.lstrip('-'), not property.startswith('-')))
        return self

    def filter(self, property_operator, value):
        match = self._PROPERTY_RE.match(property_operator)
        if not match:
            raise Exception('Invalid property_operator: %s'
                            % property_operator)
        operator = (match.groups()[1] or '=').strip().lower()
        self._filters.append((match.groups()[0], operator, value))
        return self

    def get(self):
        results = self.fetch(1)
        if results:
            return results[0]

    def _cmp_items(self, x, y):
        for property, asc in self._orders:
            c = cmp(getattr(x, property), getattr(y, property))
            if c != 0:
                return asc and c or c * -1
        return 0

    def _normalize_parameter(self, value):
        if isinstance(value, Model):
            return value.key()
        return value

    def _retrieve_ordered(self):
        if self._filters and \
           hasattr(self._model._mapper, 'filter_by_%s' % self._filters[0][0]):
            retriever = getattr(
                self._model._mapper, 'filter_by_%s' % self._filters[0][0])
            retriever = retriever(self._filters[0][2])
        else:
            retriever = self._model._mapper.retrieve_all()
        gen = (self._model._from_atom(item) for item in retriever)
        if not self._orders:
            return gen
        items = list(gen)
        items.sort(cmp=self._cmp_items)
        return items

    def __iter__(self):
        for item in self._retrieve_ordered():
            for property, operator, value in self._filters:
                item_value = getattr(item, property)
                item_value = self._normalize_parameter(item_value)
                if not self._FUNCS[operator](item_value, value):
                    break
            else:
                yield item

    def fetch(self, limit, offset=0):
        """Fetch given number of elements from a feed provided by
        AtomMapper.retrieve_all().

        """
        items = []
        limit = max(0, limit)
        for i, item in enumerate(self):
            if i < limit:
                items.append(item)
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
            if hasattr(atom, attr):
                atom = getattr(atom, attr)
            else:
                return None
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
        args = args or ('',)
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

    def get_value_for_datastore(self, model_instance):
        """Get key of reference rather than reference itself."""
        return getattr(model_instance, self.__id_attr_name())

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
        if isinstance(model_instance, Model):
            query = GDataQuery(self.__model)
        elif isinstance(model_instance, db.Model):
            query = db.Query(self.__model)
        else:
            return self

        return query.filter(self.__property + ' =', model_instance.key())


class EmbeddedModelProperty(StringProperty):
    def __init__(self, reference_class, *args, **kwargs):
        self.reference_class = reference_class
        args = args or ('',)
        super(EmbeddedModelProperty, self).__init__(*args, **kwargs)

    def make_value_from_atom(self, atom):
        value = super(EmbeddedModelProperty, self).make_value_from_atom(atom)
        return self.reference_class._from_atom(value)

    def set_value_on_atom(self, atom, value):
        super(EmbeddedModelProperty, self).set_value_on_atom(atom, value._atom)


class ListProperty(StringProperty):
    def __init__(self, item_type, attr, *args, **kwargs):
        self.item_type = item_type
        kwargs.setdefault('default', [])
        super(ListProperty, self).__init__(attr, *args, **kwargs)

    def make_value_from_atom(self, atom):
        values = super(ListProperty, self).make_value_from_atom(atom)
        return [self.item_type._from_atom(x) for x in values]

    def set_value_on_atom(self, atom, value):
        """Set the property value at the given place within the atom object.

        """
        value = [value._atom for value in value]
        super(ListProperty, self).set_value_on_atom(atom, value)


class _GDataModelMetaclass(db.PropertiedClass):
    def __new__(cls, name, bases, attrs):
        new_cls = super(_GDataModelMetaclass, cls).__new__(cls, name, bases, attrs)
        if name == 'Model':
            return new_cls

        new_cls._mapper = new_cls.Mapper
        del new_cls.Mapper

        return new_cls


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

    def __repr__(self):
        return '<%s: %s>' % (self.__class__.__name__, self.key())

    def __cmp__(self, other):
        if not isinstance(other, self.__class__):
            return -2
        kinds = cmp(self.kind(), other.kind())
        return kinds == 0 and cmp(self.key(), other.key()) or kinds

    def key(self):
        return self._mapper.key(self._atom)

    @classmethod
    def all(cls):
        return GDataQuery(cls)

    def save(self):
        atom = self._atom and _clone_atom(self._atom) or \
                self._mapper.empty_atom()
        for prop in self._properties.itervalues():
            prop.set_value_on_atom(atom, getattr(self, prop.name))
        if self.is_saved():
            if not hasattr(self._mapper, 'update'):
                raise Exception('Mapper %s doesn\'t support model updates.' %
                                self._mapper)
            if hasattr(self._mapper, 'update'):
                self._atom = self._mapper.update(atom, self._atom)
            else:
                self._atom = atom
        else:
            if hasattr(self._mapper, 'create'):
                self._atom = self._mapper.create(atom)
            else:
                self._atom = atom
    put = save

    def delete(self):
        self._mapper.delete(self._atom)
        del self

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
        return atom and cls._from_atom(atom) or None

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


class _GDataServiceDescriptor(object):
    """This object makes sure that ProgrammaticLogin() is called before the
    gdata.GDataService objects is used for the first time and it makes sure that
    it's called only once.

    It's a Python descriptor:

    http://docs.python.org/reference/datamodel.html#implementing-descriptors

    """
    def __get__(self, instance, owner):
        from crlib import users
        user = users.get_current_user()
        if not user:
            raise users.LoginRequiredError()
        user.client_login(instance._service)
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
        if hasattr(self, 'create_service'):
            self._service = self.create_service(*args, **kwargs)
        else:
            self._service = None


class UserEntryMapper(AtomMapper):
    @classmethod
    def create_service(cls):
        from gdata.apps import service
        return service.AppsService()

    def empty_atom(self):
        from gdata import apps
        return apps.UserEntry(
            login=apps.Login(),
            name=apps.Name(),
            quota=apps.Quota(),
        )

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

    def key(self, atom):
        return atom.login.user_name

    def delete(self, atom):
        self.service.DeleteUser(atom.login.user_name)


class NicknameEntryMapper(AtomMapper):
    create_service = UserEntryMapper.create_service

    def empty_atom(self):
        from gdata import apps
        return apps.NicknameEntry(
            nickname=apps.Nickname(),
            login=apps.Login(),
        )

    def create(self, atom):
        return self.service.CreateNickname(
            atom.login.user_name, atom.nickname.name)

    def retrieve_all(self):
        return self.service.RetrieveAllNicknames().entry

    def retrieve(self, nickname):
        return self.service.RetrieveNickname(nickname)

    def key(self, atom):
        return atom.nickname.name

    def filter_by_user_name(self, user_name):
        return self.service.RetrieveNicknames(user_name).entry

    def delete(self, atom):
        self.service.DeleteNickname(atom.nickname.name)

    #@filter('user')
    #def filter_by_user(self, user_name):
    #    return self.service.RetrieveNicknames(user_name).entry


class EmailTypeProperty(StringProperty):
    from gdata.contacts import REL_WORK, REL_HOME, REL_OTHER
    _RELS = (
        (REL_WORK, 'work'),
        (REL_HOME, 'home'),
        (REL_OTHER, 'other'),
    )
    _ATOM_TO_MODEL = dict(_RELS)
    _MODEL_TO_ATOM = dict([(x[1], x[0]) for x in _RELS])

    def make_value_from_atom(self, atom):
        value = super(EmailTypeProperty, self).make_value_from_atom(atom)
        return self._ATOM_TO_MODEL.get(value, 'work')

    def set_value_on_atom(self, atom, value):
        value = self._MODEL_TO_ATOM.get(value, self.REL_WORK)
        super(EmailTypeProperty, self).set_value_on_atom(atom, value)


class ContactEmailMapper(AtomMapper):
    def empty_atom(self):
        from gdata import contacts
        return contacts.Email()

    def key(self, atom):
        return atom.address


class ExtendedPropertyMapper(AtomMapper):
    def empty_atom(self):
        from gdata import ExtendedProperty
        return ExtendedProperty()

    def key(self, atom):
        return atom.name


class SharedContactEntryMapper(AtomMapper):
    @classmethod
    def create_service(cls):
        from gdata.contacts import service
        domain = settings.APPS_DOMAIN
        service = service.ContactsService()
        service.contact_list = domain
        return service

    def empty_atom(self):
        import atom
        from gdata import contacts
        return contacts.ContactEntry(
            title=atom.Title(),
            content=atom.Content(),
        )

    def key(self, atom):
        return atom.title.text

    def retrieve(self, name):
        # Shared Contacts API doesn't have any method to directly retrieve
        # ContactEntry via email or contact name, so we have to retrieve all
        # contacts and find the one with given email manually
        #for entry in self.service.GetContactsFeed().entry:
        for entry in self.retrieve_all():
            if entry.title.text == name:
                return entry

    def create(self, atom):
        return self.service.CreateContact(atom)

    def update(self, atom, old_atom):
        return self.service.UpdateContact(atom.GetEditLink().href, atom)

    def delete(self, atom):
        self.service.DeleteContact(atom.GetEditLink().href)

    def retrieve_all(self, limit=100, offset=0):
        from gdata.contacts.service import ContactsQuery
        feed_uri = self.service.GetFeedUri()
        query = ContactsQuery(feed_uri)
        query.max_results = limit
        query.start_index = offset + 1
        feed = self.service.GetContactsFeed(query.ToUri())
        return feed.entry

