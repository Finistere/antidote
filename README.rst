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
  :target: http://antidote.readthedocs.io/en/stable/?badge=stable

Antidotes is a declarative dependency injection micro-framework for Python 3.5+
which tries to do the following:

- Injection can applied on any existing code easily.
- Finding the source and the usage of a dependency is straightforward (through
  an IDE's "Go to definition" / "Find usage").
- Core functionality is flexible and extendable to support any custom dependencies.
- Limit performance impact of injection.

Why ?
=====

In short antidote avoids you the hassle of instantiating and managing your
services. You declare them at their definition, and inject them wherever
needed with simple decorators, which
*do not change how you interact with your objects*. Unit testing is not
impacted as one can override any injection and control the available
dependencies easily.

For the longer version: `<https://antidote.readthedocs.io/en/stable/why.html>`_


Features Highlight
==================

Core functionalities:

- Injection done through type hints and optionally from argument's name and/or
  with explicitly specified dependencies.
- Dependency cycle detection
- Thread-safety and limited performace impact (see
  `injection benchmark <https://github.com/Finistere/antidote/blob/master/benchmark.ipynb>`_).
- Easily extendable, through dependency providers. All aftermetioned dependencies are
  implemented with it.

Dependencies:

- Services and factories: provides an instance of a class.
- Tags: Dependencies can be tagged, and as such all of them matching a specific tag can be
  retrieved.
- Configuration: Constants which are lazily evaluated.
- Lazy function calls: Results of a function call is lazily provided.


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

    import antidote


    class Database:
        """
        Class from an external library.
        """
        def __init__(self, *args, **kwargs):
            """ Initializes the database. """

    # Usage of constants for configuration makes refactoring easier and is
    # less error-prone. Moreover Conf will only be instantiated if necessary.
    class Conf(metaclass=antidote.LazyConstantsMeta):
        DB_HOST = 'db.host'
        DB_USER = 'db.user'
        DB_PORT = 'db.port'
        DB_PASSWORD = 'db.password'

        def __init__(self):
            # Load configuration from somewhere
            self._raw_conf = {
                'db.host': 'host',
                'db.user': 'user',
                'db.port': 5432,
                'db.password': 'password'
            }

        def __call__(self, key):
            return self._raw_conf[key]


    # Declare a factory which should be called to instantiate Database.
    # The order of the arguments is here used to map the dependencies.
    # A dictionary mapping arguments name to their dependency could also
    # have been used.
    @antidote.factory(dependencies=(Conf.DB_HOST, Conf.DB_PORT,
                                    Conf.DB_USER, Conf.DB_PASSWORD))
    def database_factory(host: str, port: int, user: str, password: str) -> Database:
        """
        Configure your database.
        """
        return Database(host=host, port=port, user=user, password=password)

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
    conf = Conf()
    f(DatabaseWrapper(database_factory(
        host=conf.DB_HOST,  # equivalent to conf._raw_conf['db.host']
        port=conf._raw_conf['db.port'],
        user=conf._raw_conf['db.user'],
        password=conf._raw_conf['db.password']
    )))


Documentation
=============


The documentation is available at
`<https://antidote.readthedocs.io/en/stable>`_.

Injection benchmark is available at
`injection benchmarks <https://github.com/Finistere/antidote/blob/master/benchmark.ipynb>`_.


Bug Reports / Feature Requests
==============================


Any feedback is always welcome, feel free to submit issues and enhancement
requests ! :)
For any questions, open an issue on Github.


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
- create features difficult to understand for an IDE, such as converting a
  string *dependency id* to a non singleton object somehow. An user may do
  this, but antidote shouldn't.

Pull requests **will not** be accepted if:

- classes and non trivial functions have not docstrings documenting their
  behavior.
- tests do not cover all of code changes.


*Do not hesitate to send a pull request, even if incomplete, to get early
feedback ! :)*
