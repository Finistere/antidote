Dependency Manager
==================

*Dependency Manager* is dependency injection module for Python 2.7 and 3.4+. It
was designed to work with simple decorators which infer all the configuration 
from type annotations.

Key features are:
- Dependencies bound through type annotations and optionally from variable 
names and/or mapping.
- Simple decorators to handle pretty much everything.
- Standard dependency injection features: singleton, factories (provider), 
auto-wiring
- Python 2.7 support (without annotations, obviously :))
- Compatibility with the [attrs](http://www.attrs.org/en/stable/) package (>= v17.1).
- Configuration parameters can be easily added for injection.


Status
------

The project is still under construction.


Usage
-----

### Quick Start

A simple example with a external database for which you have an adapter which
will be injected in other services.

For Python 3.4+, the dependency is straight-forward:

```python
import dependency_manager as dym


class Database(object):
    """
    Class from an external library.
    """
    def __init__(self, *args, **kwargs):
        """ Initializes the database. """

# Simple way to add some configuration.
dym.container.append(dict(
    database_host='host',
    database_user='user',
    database_password='password',
))

# Variables names will be used for injection.
@dym.provider(use_arg_name=True)
def database_factory(database_host, database_user, database_password) -> Database:
    """
    Configure your database.
    """
    return Database(
        host=database_host,
        user=database_user,
        password=database_password
    )


@dym.register
class DatabaseAdapter(object):
    """
    Your class to manage the database.
    """
    def __init__(self, db: Database):
        self.db = db
    
    # other methods
    
@dym.inject
def f(db: DatabaseAdapter):
    """ Do something with your database. """    
```

For Python 2, the example is a bit more verbose as you need to compensate for 
the lack of annotations:

```python
import dependency_manager as dym


class Database(object):
    """
    Class from an external library.
    """
    def __init__(self, *args, **kwargs):
        """ Initializes the database. """

# Simple way to add some configuration.
dym.container.append(dict(
    database_host='host',
    database_user='user',
    database_password='password',
))

# Variables names will be used for injection.
@dym.provider(use_arg_name=True, returns=Database)
def database_factory(database_host, database_user, database_password):
    """
    Configure your database.
    """
    return Database(
        host=database_host,
        user=database_user,
        password=database_password
    )


@dym.register(mapping=dict(db=Database))
class DatabaseAdapter(object):
    """
    Your class to manage the database.
    """
    def __init__(self, db):
        self.db = db
    
    # other methods
    
@dym.inject(mapping=dict(db=DatabaseAdapter))
def f(db):
    """ Do something with your database. """      
```


TODO
------

- Better support for configuration ?
- proxies ?
