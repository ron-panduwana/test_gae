# Exceptions

class GDataError(Exception): pass


class EntityDeletedRecentlyError(GDataError):
    """ The request instructs Google to create a new entity but uses
    the name of an entity that was deleted in the previous five days.

    """


class DomainUserLimitExceededError(GDataError):
    """ The specified domain has already reached its quota of user accounts.
    
    """


class EntityExistsError(GDataError):
    """ The request instructs Google to create an entity that already exists.

    """


class EntityDoesNotExistError(GDataError):
    """ The request asks Google to retrieve an entity that does not exist.

    """


class EntityNameNotValidError(GDataError):
    """ The request provides an invalid name for a requested resource.

    """


class InvalidValueError(GDataError):
    """ An value specified is not valid.

    """


class EntitySizeTooLarge(GDataError):
    pass


class UnknownGDataError(GDataError):
    """ This is temporary used to validate existing group emails when creating
    new user. Please refer to story 4055432.
    """ 


class NetworkError(GDataError):
    pass


APPS_FOR_YOUR_DOMAIN_ERROR_CODES = {
    1100: EntityDeletedRecentlyError,
    1200: DomainUserLimitExceededError,
    1300: EntityExistsError,
    1301: EntityDoesNotExistError,
    1303: EntityNameNotValidError,
    1801: InvalidValueError,
    1000: UnknownGDataError,
}


def apps_for_your_domain_exception_wrapper(func):
    from google.appengine.api.urlfetch_errors import DownloadError
    from gdata.apps.service import AppsForYourDomainException
    def new(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except AppsForYourDomainException, e:
            exception = APPS_FOR_YOUR_DOMAIN_ERROR_CODES.get(e.error_code)
            if exception:
                raise exception()
            raise
        except DownloadError:
            raise NetworkError
    new.__name__ = func.__name__
    new.__doc__ = func.__doc__
    return new

