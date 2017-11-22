.. image:: https://travis-ci.org/Finistere/dependency_manager.svg?branch=master
  :target: https://travis-ci.org/Finistere/dependency_manager

.. image:: https://codecov.io/gh/Finistere/dependency_manager/branch/master/graph/badge.svg
  :target: https://codecov.io/gh/Finistere/dependency_manager

.. image:: https://readthedocs.org/projects/dependency-manager/badge/?version=latest
  :target: http://dependency-manager.readthedocs.io/en/latest/?badge=latest
  :alt: Documentation Status

******************
Dependency Manager
******************

*Dependency Manager* is dependency injection module for Python 2.7 and 3.4+. It
was designed to work with simple decorators which infer all the configuration 
from type annotations. Key features are:

- Dependencies bound through type annotations and optionally from variable 
  names and/or mapping.
- Simple decorators to handle pretty much everything.
- Standard dependency injection features: singleton, factories (provider), 
  auto-wiring
- Python 2.7 support (without annotations, obviously :))
- Integration with the `attrs <http://www.attrs.org/en/stable/>`_ package
  (>= v17.1).
- Other dependencies, such as configuration parameters, can be easily added
  for injection as a dictionary.


Quick Start
===========

A simple example with a external database for which you have an adapter which
will be injected in other services.

For Python 3.4+, the dependency management is straight-forward:

.. code-block:: python

    import dependency_manager as dym

    class Database(object):
        """
        Class from an external library.
        """
        def __init__(self, *args, **kwargs):
            """ Initializes the database. """

    # Simple way to add some configuration.
    dym.container.extend(dict(
        database_host='host',
        database_user='user',
        database_password='password',
    ))

    # Variables names will be used for injection.
    @dym.factory(use_arg_name=True)
    def database_factory(database_host, database_user, database_password) -> Database:
        """
        Configure your database.
        """
        return Database(
            host=database_host,
            user=database_user,
            password=database_password
        )


    @dym.service
    class DatabaseWrapper(object):
        """
        Your class to manage the database.
        """

        # Dependencies of __init__() are injected by default when registering
        # a dependency.
        def __init__(self, db: Database):
            self.db = db


    @dym.inject
    def f(db: DatabaseWrapper):
        """ Do something with your database. """

For Python 2, the example is a bit more verbose as you need to compensate for 
the lack of annotations:

.. code-block:: python

    import dependency_manager as dym


    class Database(object):
        """
        Class from an external library.
        """
        def __init__(self, *args, **kwargs):
            """ Initializes the database. """

    # Simple way to add some configuration.
    dym.container.extend(dict(
        database_host='host',
        database_user='user',
        database_password='password',
    ))

    # Variables names will be used for injection.
    @dym.factory(use_arg_name=True, id=Database)
    def database_factory(database_host, database_user, database_password):
        """
        Configure your database.
        """
        return Database(
            host=database_host,
            user=database_user,
            password=database_password
        )


    @dym.service(mapping=dict(db=Database))
    class DatabaseWrapper(object):
        """
        Your class to manage the database.
        """

        # Dependencies of __init__() are injected by default when registering
        # a dependency.
        def __init__(self, db):
            self.db = db


    @dym.inject(mapping=dict(db=DatabaseWrapper))
    def f(db):
        """ Do something with your database. """


TODO
====

- Better support for configuration ?
- proxies ?
