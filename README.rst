********
Antidote
********


.. image:: https://img.shields.io/pypi/v/antidote.svg
  :target: https://pypi.python.org/pypi/antidote

.. image:: https://img.shields.io/pypi/l/antidote.svg
  :target: https://pypi.python.org/pypi/antidote

.. image:: https://img.shields.io/pypi/pyversions/antidote.svg
  :target: https://pypi.python.org/pypi/antidote

.. image:: https://travis-ci.org/Finistere/antidote.svg?branch=master
  :target: https://travis-ci.org/Finistere/antidote

.. image:: https://codecov.io/gh/Finistere/antidote/branch/master/graph/badge.svg
  :target: https://codecov.io/gh/Finistere/antidote

.. image:: https://readthedocs.org/projects/antidote/badge/?version=latest
  :target: http://antidote.readthedocs.io/en/latest/?badge=latest

*Antidote* is a dependency injection micro framework for Python 2.7 and 3.4+.
It provides simple decorators to declare services and to inject those
automatically based on type hints.


Features Highlight
==================


- Dependencies bound through type hints and optionally from variable names
  and/or mapping.
- Integrates well with any code, injected functions can be called as usual
  with all their arguments.
- Standard dependency injection features: singleton, factories, auto-wiring
  (automatically injecting dependencies of defined services)
- Dependency cycle detection.
- Thread-safe and limited performance impact (see
  `injection benchmark <https://github.com/Finistere/antidote/blob/master/benchmark.ipynb>`_).
- Python 2.7 support (without type hints, obviously :))
- Integration with the `attrs <http://www.attrs.org/en/stable/>`_ package
  (>= v17.1).
- Other dependencies, such as configuration parameters, can be easily added
  for injection as a dictionary.


Installation
============


To install Antidote, simply run this command:

.. code-block:: bash

    pip install antidote


Quick Start
===========


Let's suppose you have database class from an external library and you wrap it
with a custom class for easier usage. Antidote can do all the wiring for you.

With type hints, it is straight-forward:

.. code-block:: python

    import antidote

    class Database(object):
        """
        Class from an external library.
        """
        def __init__(self, *args, **kwargs):
            """ Initializes the database. """

    # Simple way to add some configuration.
    antidote.world.update(dict(
        db_host='host',
        db_user='user',
        db_password='password',
    ))

    # Declare a factory which should be called to instantiate Database
    # Variables names are used here for injection.
    @antidote.factory(use_names=True)
    def database_factory(db_host, db_user, db_password) -> Database:
        """
        Configure your database.
        """
        return Database(
            host=db_host,
            user=db_user,
            password=db_password
        )

    # Declare DatabaseWrapper as a service to be injected
    @antidote.register
    class DatabaseWrapper(object):
        """
        Your class to manage the database.
        """

        # Dependencies of __init__() are injected by default when
        # registering a service.
        def __init__(self, db: Database):
            self.db = db


    @antidote.inject
    def f(db: DatabaseWrapper):
        """ Do something with your database. """

    # Can be called without arguments now.
    f()

    # You can still explicitly pass the arguments for testing
    # for example.
    f(DatabaseWrapper(database_factory(
        db_host='host',
        db_user='user',
        db_password='password'
    )))

For Python 2, the example is a bit more verbose as you need to compensate for
the lack of annotations:

.. code-block:: python

    import antidote


    class Database(object):
        """
        Class from an external library.
        """
        def __init__(self, *args, **kwargs):
            """ Initializes the database. """

    # Simple way to add some configuration.
    antidote.world.update(dict(
        db_host='host',
        db_user='user',
        db_password='password',
    ))

    # Declare a factory which should be called to instantiate Database
    # Variables names are used here for injection.
    # PY2: The id of the returned service is specified
    @antidote.factory(use_names=True, id=Database)
    def database_factory(db_host, db_user, db_password):
        """
        Configure your database.
        """
        return Database(
            host=db_host,
            user=db_user,
            password=db_password
        )

    # Declare DatabaseWrapper as a service to be injected
    # PY2: A class-wide argument -> dependency mapping is specified,
    @antidote.register(mapping=dict(db=Database))
    class DatabaseWrapper(object):
        """
        Your class to manage the database.
        """

        # Dependencies of __init__() are injected by default when
        # registering a service.
        def __init__(self, db):
            self.db = db

    # PY2: An argument -> dependency mapping is specified
    @antidote.inject(mapping=dict(db=DatabaseWrapper))
    def f(db):
        """ Do something with your database. """

    # Can be called without arguments now.
    f()

    # You can still explicitly pass the arguments for testing
    # for example.
    f(DatabaseWrapper(database_factory(
        db_host='host',
        db_user='user',
        db_password='password'
    )))



Documentation
=============


The documentation is available at
`<https://antidote.readthedocs.io/>`_.

Injection benchmark is available at
`injection benchmarks <https://github.com/Finistere/antidote/blob/master/benchmark.ipynb>`_.


Why Antidote ?
==============


Dependency injection is, IMHO, a fundamental tool when working on projects.
Your thinking about dependencies will shift from *"I need to retrieve,
instantiate and provide my service with dependencies"* to *"I need those
dependencies"*. The rest is handled through dependency injection.

As your project grows the more necessary it becomes to decouple your code. If
you change how a service is created, it does not affect code depending on it.
With dependency injection, you only need to specify how and with which
dependencies a service needs to be used, once at its definition.

So while searching for a dependency injection library, I had three requirements
in mind:

- Use of type hints to inject dependencies. And provide other means to specify
  dependencies as configuration parameters cannot be injected this way for
  example.
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
requirements. Here is partial list of project and why they do not fulfill
previously stated requirements (at the 26/11/17):

- `Dependency Injector <https://github.com/ets-labs/python-dependency-injector>`_:
  Does not use type hints, which leads to a lot of boilerplate code IMHO.
- `Siringa <https://github.com/h2non/siringa>`_: Does not use type hints but
  custom annotations with for :code:`'!'` to specify dependencies to be
  injected.
- `PyCDI <https://github.com/ettoreleandrotognoli/python-cdi>`_: Need to use
  :code:`call()` to execute a function. This is, IMHO, not a proper design for
  dependency injection, you either need to use :code:`call()` on all your entry
  points, or know which functions needs it. This makes it harder to use on
  existing projects.
- `Injector <https://github.com/alecthomas/injector>`_: Need to retrieve a
  service with the :code:`Injector`. Same issue as the previous library.


How to Contribute
=================


1. Check for open issues or open a fresh issue to start a discussion around a
   feature or a bug.
2. Fork the repo on GitHub. Run the tests to confirm they all pass on your
   machine. If you cannot find why it fails, open an issue.
3. Start making your changes to the master branch.
4. Writes tests which shows that your code is working as intended. (This also
   means 100% coverage.)
5. Send a pull request.

.. note::

    Be sure to merge the latest from "upstream" before making a pull request!


Pull requests **should avoid** to:

- make it harder to integrate Antidote into existing code.
- break backwards compatibility.

Pull requests **will not** be accepted if:

- classes and non trivial functions have not docstrings documenting their
  behavior.
- tests do not cover all of code changes.


.. note::

    Do not hesitate to send a pull request, even if incomplete, to get early
    feedback ! :)


Bug Reports / Feature Requests
==============================


Any feedback is always welcome, feel free to submit issues and enhancement
requests ! :)


TODO
====

This actually more of a roadmap of features. Those marked with a "(?)" may not
be implemented.

- Better support for configuration (ConfigParser typically) with a provider.
- tags to filter services and retrieve a list of them.
- type hints in Antidote's source code.
- find a way to test absence of attrs with pytest as it now depends on it.
- use pipenv
- use python 2 type hints (?)
- way to restrict services availability, either through tags, different
  containers or injectors, etc... (?)
- proxies (?)
