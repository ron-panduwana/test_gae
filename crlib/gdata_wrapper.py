import datetime
import hashlib
import logging
import operator
import os
import pickle
import re
from django.conf import settings
from google.appengine.ext import db
from google.appengine.api import memcache
from atom import AtomBase
from gdata.data import ExtendedProperty
from gdata.client import GDClient
from gdata.service import GDataService
from crauth import users
from crlib.signals import class_prepared
from crlib import cache
from crlib.models import GDataIndex


BadValueError = db.BadValueError


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
        cache.ensure_has_cache(
            users.get_current_user().domain_name, model_class.__name__)

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

    def _retrieve_ordered(self, limit=1000, offset=0):
        can_retrieve_subset = not self._filters and \
                hasattr(self._model._mapper, 'retrieve_subset')
        if self._filters and \
           hasattr(self._model._mapper, 'filter_by_%s' % self._filters[0][0]):
            retriever = getattr(
                self._model._mapper, 'filter_by_%s' % self._filters[0][0])
            retriever = retriever(
                self._normalize_parameter(self._filters[0][2]))
        elif can_retrieve_subset:
            retriever = self._model._mapper.retrieve_subset(limit, offset)
        else:
            retriever = self._model._cache['retrieve_all']
            if retriever is None:
                retriever = self._model._mapper.retrieve_all()
                self._model._cache['retrieve_all'] = retriever
        gen = (self._model._from_atom(item) for item in retriever)
        if not self._orders:
            return gen
        items = sorted(gen, cmp=self._cmp_items)
        if not can_retrieve_subset:
            items = items[offset:offset+limit]
        return items

    def _matches_filter(self, item):
        for i, (property, operator, value) in enumerate(self._filters):
            # Skip the check if the mapper has filter_by_property method
            if i == 0 and \
               hasattr(self._model._mapper, 'filter_by_%s' % property):
                continue
            item_value = getattr(item, property)
            item_value = self._normalize_parameter(item_value)
            if hasattr(item_value, '__iter__') and operator in ('=', 'in'):
                return value in item_value
            if not self._FUNCS[operator](item_value, value):
                return False
        else:
            return True

    def _retrieve_cached(self, limit=1000, offset=0):
        cache_model = self._model._meta.cache_model
        domain = users.get_current_domain().domain
        query = cache_model.all().filter('_domain', domain)

        for prop, operator, value in self._filters:
            if isinstance(value, Model):
                value = value.key()
            query.filter('%s %s' % (prop, operator), value)

        return query.fetch(limit, offset)

    def _retrieve_filtered(self, limit=1000, offset=0):
        use_cache = hasattr(self._model._meta, 'cache_model')
        if use_cache:
            for prop, _, _ in self._filters:
                if not hasattr(self._model._meta.cache_model, prop):
                    use_cache = False
                    break
        if use_cache:
            for item in self._retrieve_cached(limit, offset):
                yield self._model._from_cached(item)
        else:
            for item in self._retrieve_ordered(limit, offset):
                if self._matches_filter(item):
                    yield item

    __iter__ = _retrieve_filtered

    def fetch(self, limit, offset=0):
        """Fetch given number of elements from a feed provided by
        AtomMapper.retrieve_all().

        """
        return list(self._retrieve_filtered(limit, offset))

    def retrieve_page(self, cursor=None):
        page, cursor = self._model._mapper.retrieve_page(cursor)
        gen = (self._model._from_atom(item) for item in page)
        return (gen, page, cursor)


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
        choices = kwargs.pop('choices', None)
        if choices is not None:
            kwargs['choices'] = [x[0] for x in choices]
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


class DateProperty(StringProperty):
    DATE_FORMAT = '%Y-%m-%d'

    def make_value_from_atom(self, atom):
        value = super(DateProperty, self).make_value_from_atom(atom)
        if value:
            return datetime.datetime.strptime(value, self.DATE_FORMAT).date()

    def set_value_on_atom(self, atom, value):
        if value:
            value = value.strftime(self.DATE_FORMAT)
            super(DateProperty, self).set_value_on_atom(atom, value)


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
        if value is not None:
            return self.reference_class._from_atom(value)

    def set_value_on_atom(self, atom, value):
        super(EmbeddedModelProperty, self).set_value_on_atom(
            atom, value and value._atom or None)


class ListProperty(StringProperty):
    def __init__(self, item_type, attr, *args, **kwargs):
        self.item_type = item_type
        kwargs.setdefault('default', [])
        super(ListProperty, self).__init__(attr, *args, **kwargs)

    def __get__(self, model_instance, model_class):
        values = getattr(model_instance, self._attr_name())
        if values == 'NOT_RESOLVED':
            values = super(ListProperty, self).make_value_from_atom(
                model_instance._atom) or []
            values = [self.item_type._from_atom(x) for x in values]
            setattr(model_instance, self._attr_name(), values)
        return values

    def make_value_from_atom(self, atom):
        return 'NOT_RESOLVED'

    def set_value_on_atom(self, atom, value):
        """Set the property value at the given place within the atom object.

        """
        value = [value._atom for value in value]
        super(ListProperty, self).set_value_on_atom(atom, value)

class ExtendedPropertyMapping(StringProperty):
    MAX_EXTENDED_PROPERTIES = 10

    def make_value_from_atom(self, atom):
        values = super(ExtendedPropertyMapping, self).make_value_from_atom(atom)
        mapping = {}
        for value in values:
            mapping[value.name] = value.value
        return mapping

    def set_value_on_atom(self, atom, value):
        if not value:
            return

        values = []
        for key, value in value.iteritems():
            if value:
                values.append(ExtendedProperty(name=key, value=value))

        if len(values) > self.MAX_EXTENDED_PROPERTIES:
            raise BadValueError('There may be up to %d extended properties.' %
                                self.MAX_EXTENDED_PROPERTIES)

        super(ExtendedPropertyMapping, self).set_value_on_atom(atom, values)


class _MemcacheDict(object):
    def __init__(self, namespace, time=0):
        self.namespace = namespace
        self.time = time

    def _key(self, key):
        domain = users.get_current_user().domain_name
        return '%s:%s' % (domain, key)

    def __getitem__(self, key):
        return memcache.get(self._key(key), namespace=self.namespace)

    def __setitem__(self, key, value):
        try:
            memcache.set(self._key(key), value, namespace=self.namespace, time=self.time)
        except TypeError:
            logging.warning('Couldn\'t store a value in memcache.')

    def __delitem__(self, key):
        memcache.delete(self._key(key), namespace=self.namespace)


class _GDataModelMetaclass(db.PropertiedClass):
    def __new__(cls, name, bases, attrs):
        new_cls = super(_GDataModelMetaclass, cls).__new__(
            cls, name, bases, attrs)
        if name == 'Model':
            return new_cls

        new_cls._mapper = new_cls.Mapper
        new_cls._meta = getattr(new_cls, 'Meta', None)
        if hasattr(new_cls, 'Meta'):
            del new_cls.Meta
        del new_cls.Mapper

        if hasattr(new_cls._meta, 'cache_model'):
            cache.register(new_cls)

        new_cls._cache = _MemcacheDict(name, 60 * 60)
        class_prepared.send(sender=new_cls)

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
        self._cached = kwargs.pop('_cached', None)

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

    def _get_updated_atom(self):
        if self._atom:
            atom = self._mapper.clone_atom(self._atom)
        else:
            atom = self._mapper.empty_atom()

        # Create Atom elements for missing properties
        if hasattr(self._mapper, 'optional'):
            for k, v in self._mapper.optional.iteritems():
                if not hasattr(atom, k) or getattr(atom, k) is None:
                    setattr(atom, k, v())

        for prop in self._properties.itervalues():
            prop.set_value_on_atom(atom, getattr(self, prop.name))

        # Filter out empty properties
        if hasattr(self._mapper, 'optional'):
            for prop_name in self._mapper.optional.iterkeys():
                prop = getattr(atom, prop_name)
                if prop is None or not prop.text:
                    setattr(atom, prop_name, None)

        return atom

    def save(self):
        if settings.READ_ONLY:
            return self

        atom = self._get_updated_atom()

        if self.is_saved():
            if hasattr(self._mapper, 'update'):
                self._atom = self._mapper.update(atom, self._atom)
            else:
                self._atom = atom
            self._update_cache()
        else:
            if hasattr(self._mapper, 'create'):
                self._atom = self._mapper.create(atom)
            else:
                self._atom = atom
            self._create_cache()

        del self._cache['item:%s' % self.key()]
        del self._cache['retrieve_all']
        return self
    put = save

    def delete(self):
        if not settings.READ_ONLY:
            self._mapper.delete(self._atom)
            self._delete_cache()
            del self._cache['item:%s' % self.key()]
            del self._cache['retrieve_all']
            del self

    def is_saved(self):
        return self._atom is not None

    def _update_cache(self):
        if self._cached:
            self._cached.update(self)
            self._cached._index.page_hash = '!'
            db.put([self._cached, self._cached._index])

    def _get_index_for_new_cache(self, domain):
        model_class = self.__class__.__name__
        index = GDataIndex.all().filter('domain', domain).filter(
            'model_class', model_class).filter(
                'keys >', self.key()).order('keys').get()
        if not index:
            index = GDataIndex.all().filter('domain', domain).filter(
                'model_class', model_class).order('-keys').get()
        return index

    def _create_cache(self):
        if hasattr(self._meta, 'cache_model'):
            new_key = self.key()
            hsh = hashlib.sha1(str(self._atom)).hexdigest()
            domain = users.get_current_domain().domain
            index = self._get_index_for_new_cache(domain)
            cached = self._meta.cache_model.from_model(
                self,
                key_name=hsh,
                _domain=domain,
                _atom=self._atom,
                _index=index,
                _gdata_key_name=new_key,
            )
            for i, key in enumerate(index.keys):
                if key > new_key:
                    break
            index.keys.insert(i, new_key)
            index.hashes.insert(i, hsh)
            index.page_has = '!'
            db.put([cached, index])
            return cached

    def _delete_cache(self):
        if self._cached:
            index = self._cached._index
            index.page_hash = '!'
            idx = index.keys.index(self.key())
            del index.keys[idx]
            del index.hashes[idx]
            index.put()
            self._cached.delete()

    @classmethod
    def kind(cls):
        return cls.__name__

    @classmethod
    def get_by_key_name(cls, key_name):
        atom = cls._cache['item:%s' % key_name]
        if atom is None:
            if hasattr(cls._meta, 'cache_model'):
                domain = users.get_current_domain().domain
                cached = cls._meta.cache_model.all().filter(
                    '_domain', domain).filter(
                        '_gdata_key_name', key_name).get()
                return cls._from_cached(cached)
            else:
                try:
                    atom = cls._mapper.retrieve(key_name)
                    cls._cache['item:%s' % key_name] = atom
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

    @classmethod
    def _from_cached(cls, cached):
        import pickle
        if not cached:
            return None
        instance = cls._from_atom(pickle.loads(cached._atom))
        instance._cached = cached
        return instance


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
    @property
    def service(self):
        if not hasattr(self, 'create_service'):
            return None

        user = users.get_current_user()
        if not user:
            raise users.LoginRequiredError()

        domain = user.domain_name
        service = self.create_service(domain)
        if isinstance(service, GDataService):
            from gdata.alt.appengine import AppEngineHttpClient
            service.http_client = AppEngineHttpClient(deadline=10)
        auth_method = getattr(self, 'auth_method', 'client_login')
        if auth_method == 'oauth':
            user.oauth_login(service)
        else:
            user.client_login(service)

        return service

    def clone_atom(self, atom):
        """Make a copy of atom object."""
        from atom.core import XmlElement, parse
        from atom import CreateClassFromXMLString

        if isinstance(atom, XmlElement):
            # New version of the API
            return parse(atom.to_string(), atom.__class__)
        else:
            # Old version
            return CreateClassFromXMLString(atom.__class__, str(atom))


def simple_mapper(atom, key):
    def empty_atom(self):
        return atom()

    def _key(self, atom):
        return getattr(atom, key)

    return type(
        '%sMapper' % atom.__class__.__name__,
        (AtomMapper,), {
            'empty_atom': empty_atom,
            'key': _key,
        })

