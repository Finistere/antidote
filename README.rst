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

*Antidote* is a dependency injection micro framework for Python 3.4+.
It provides simple decorators to declare services and to inject those
automatically based on type hints.


Features Highlight
==================


- Dependencies bound through type hints and optionally from variable names
  and/or mapping.
- Integrates well with any code, injected functions can be called as usual
  with all their arguments.
- Integration with the `attrs <http://www.attrs.org/en/stable/>`_ package
  (>= v17.1).
- Thread-safe and limited performance impact (see
  `injection benchmark <https://github.com/Finistere/antidote/blob/master/benchmark.ipynb>`_).
- Dependency cycle detection.
- Other dependencies, such as configuration parameters, can be easily added.
- Easily extendable.


Installation
============


To install Antidote, simply run this command:

.. code-block:: bash

    pip install antidote


Quick Start
===========


Let's suppose you have database class from an external library and you wrap it
with a custom class for easier usage. Antidote can do all the wiring for you:


.. code-block:: python

    from antidote import antidote, Dependency as Dy
    from operator import getitem


    class Database:
        """
        Class from an external library.
        """
        def __init__(self, *args, **kwargs):
            """ Initializes the database. """

    config = {
        'db': {
            'host': 'host',
            'user': 'user',
            'port': '5432',
            'password': 'password',
        }
    }

    # Add configuration parameters.
    antidote.register_parameters(config, getter=getitem, prefix='conf:',
                                 split='.')

    # Declare a factory which should be called to instantiate Database.
    # Variables names are used here for injection. A dictionary mapping
    # arguments name to their dependency could also have been used.
    @antidote.factory(arg_map=('conf:db.host',
                               Dy('conf:db.port', coerce=int),
                               'conf:db.user',
                               'conf:db.password'))
    def database_factory(db_host, db_port, db_user,
                         db_password) -> Database:
        """
        Configure your database.
        """
        return Database(
            host=db_host,
            port=db_port,
            user=db_user,
            password=db_password
        )

    # Declare DatabaseWrapper as a service to be injected.
    @antidote.register
    class DatabaseWrapper:
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

    # You can still explicitly pass the arguments to override
    # injection.
    f(DatabaseWrapper(database_factory(
        db_host=config['db']['host'],
        db_port=int(config['db']['port']),
        db_user=config['db']['user'],
        db_password=config['db']['password']
    )))


Documentation
=============


The documentation is available at
`<https://antidote.readthedocs.io/>`_.

Injection benchmark is available at
`injection benchmarks <https://github.com/Finistere/antidote/blob/master/benchmark.ipynb>`_.


Dependency Injection
====================

Dependency injection is a technique where objects do not instantiate themselves
their dependencies, it is up to the user or another object to supply them. A
simple example is presented below: :code:`f()` and :code:`g()` are two functions
operating on a database, they both require a connection to it. :code:`g()` is
implemented with dependency injection in mind, while :code:`f()` is not.

.. code-block:: python

    class Database:
        def __init__(self, host):
            """ Initializes database """

    def f(host):
        db = Database(host)
        # do stuff

    # With dependency injection, it's up to the user/framework to
    # provide the database.
    def g(database):
        # do stuff


Using :code:`g()` provides several advantages:

- Single Responsibility Principle: The function does not have to instantiate
  anything anymore, it only does its job.
- Open/closed principle: One can change the database for any other one, as long
  as it keeps the same interface. With :code:`f()` you would need to rewrite
  the function, as the database may need to be instantiated differently.
- As you don't have to manage dependencies in you code anymore, it becomes
  usually easier to create more modular code and readable code.
- When testing, it can be easier to supply a dummy object which mimics the
  database than mocking the :code:`Database()` itself. This helps separating
  what you *need* and what you *have*.

Now you're faced with the problem of injecting and managing your dependencies.
It is, unsurprisingly, quite easy with Python for simple projects: You have
a module with your dependencies, be it singletons or factories to instantiate
them, and you inject them at the start of your applications in your scripts or
in :code:`__main__()`. While this works really well for relatively small-sized
projects with a limited number of dependencies, it doesn't scale
at all.

- Instantiation is not lazy. Often you do not need all of your dependencies and
  instantiating all of them can be costly.
- With a lot of different dependencies, it can quickly become a mess to
  properly manage them in one big file or multiple ones.
- The dependencies are defined and instantiated in different places, which is
  error-prone whenever you modify them.

The wiring and managing of all your dependencies, is what antidote is for. You
define your dependency in one place, let antidote know it exists and how to
instantiate it and you're done !


Why Antidote ?
==============

While there are several dependency injection libraries, there was none which
matched my needs or at least convinced me it could, as of 26/11/17:

- Use of type hints to inject dependencies. And provide other means to specify
  dependencies as configuration parameters cannot be injected this way for
  example.
- Standard dependency injection features: services, factories, auto-wiring...
- It has be easy to integrate with existing code.

Here is quick and non extensive list of frameworks at which I looked:

- `Dependency Injector <https://github.com/ets-labs/python-dependency-injector>`_:
  Does not use type hints, which leads to a more boilerplate code.
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

*Be sure to merge the latest from "upstream" before making a pull request!*


Pull requests **should avoid** to:

- make it harder to integrate Antidote into existing code.
- break backwards compatibility.

Pull requests **will not** be accepted if:

- classes and non trivial functions have not docstrings documenting their
  behavior.
- tests do not cover all of code changes.


*Do not hesitate to send a pull request, even if incomplete, to get early
feedback ! :)*


Bug Reports / Feature Requests
==============================


Any feedback is always welcome, feel free to submit issues and enhancement
requests ! :)
For any questions, open an issue on Github.


TODO
====

This actually more of a roadmap of features. Those marked with a "(?)" may not
be implemented.

- tags to filter services and retrieve a list of them.
- Add a proper way to test with injector.bind + mocking utility.
- way to restrict services availability, either through tags, different
  containers or injectors, etc... (?)
- proxies (?)
