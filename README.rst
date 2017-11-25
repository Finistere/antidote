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
is designed to work with simple decorators and annotations. The goal is to
recognize dependencies and inject them automatically.

Features Highlight
==================

- Dependencies bound through type annotations and optionally from variable 
  names and/or mapping.
- Simple decorators to handle pretty much everything.
- Standard dependency injection features: singleton, factories, auto-wiring
  (automatically injecting dependencies of defined services, etc.)
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

    from dependency_manager import dym, dpy

    class Database(object):
        """
        Class from an external library.
        """
        def __init__(self, *args, **kwargs):
            """ Initializes the database. """

    # Simple way to add some configuration.
    # Any object implementing __getitem__ works
    dym.container.extend(dict(
        database_host='host',
        database_user='user',
        database_password='password',
    ))

    # Declare a factory which should be called to instantiate Database
    # Variables names are used here for injection.
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

    # Declare DatabaseWrapper as a dependency to be injected
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

    from dependency_manager import dym


    class Database(object):
        """
        Class from an external library.
        """
        def __init__(self, *args, **kwargs):
            """ Initializes the database. """

    # Simple way to add some configuration.
    # Any object implementing __getitem__ works
    dym.container.extend(dict(
        database_host='host',
        database_user='user',
        database_password='password',
    ))

    # Declare a factory which should be called to instantiate Database
    # Variables names are used here for injection.
    # PY2: The id of the returned service is specified
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

    # Declare DatabaseWrapper as a dependency to be injected
    # PY2: A class-wide argument -> dependency mapping is specified,
    @dym.service(mapping=dict(db=Database))
    class DatabaseWrapper(object):
        """
        Your class to manage the database.
        """

        # Dependencies of __init__() are injected by default when registering
        # a dependency.
        def __init__(self, db):
            self.db = db

    # PY2: An argument -> dependency mapping is specified
    @dym.inject(mapping=dict(db=DatabaseWrapper))
    def f(db):
        """ Do something with your database. """


Documentation
=============

The documentation is available at
`<https://dependency-manager.readthedocs.io/>`_.


Why ?
=====

Dependency injection is, IMHO, a fundamental tool when working on projects. As
it grows the more necessary it becomes to decouple your code by defining
clearly in only one place how an object or a function should be called with
which dependencies.

So while searching for a dependency injection library, I had three requirements
in mind:

- Use of annotations compatible with type checker such as
  `mypy <https://github.com/python/mypy>`_ to inject dependencies. But other
  ways should exist, as configuration parameters cannot be injected this way
  for example.
- IMHO, the strict minimum of a dependency injection library: services,
  factories, and something to inject those in any callable which injects their
  dependencies.
- The library should be easy to integrate in existing code, be it in Python 2
  (it's not gone, yet) or 3. Ideally one should be able to use injected classes
  or functions like any other. Usage should be transparent, which leads to
  easier integration and adoption.

However, I did not found a suitable library and was actually surprised to see
that dependency injection was not commonly used in Python. So I created this
project to answer those requirements.


Related Projects
================

Different projects exist for dependency injection which did not satisfied my
requirements:

- `Dependency Injector <https://github.com/ets-labs/python-dependency-injector>`_:
  Does not use annotations, thus IMHO the code is too boilerplate.
- `Siringa <https://github.com/h2non/siringa>`_: Does not integrate well with
  `mypy <https://github.com/python/mypy>`_ with its need for :code:`'!'` to
  specify dependencies to be injected.
- `PyCDI <https://github.com/ettoreleandrotognoli/python-cdi>`_: Need to use
  :code:`call()` to execute a function.
- `Injector <https://github.com/alecthomas/injector>`_: Need to retrieve a
  service with the :code:`Injector`.


TODO
====

- Better support for configuration (ConfigParser typically)
- tags to filter services and retrieve a list of them.
- proxies ?


License
=======

MIT
