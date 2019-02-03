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

Antidotes is a declarative dependency injection micro-framework which tries to
do the following  :
- Injection can be added anywhere easily, no need to use anything else than
  decorators except for advanced features.
- It should be easy to find where dependencies are instantiated from any point
  in the code where they're injected.
- Easily extendable to support any kind of dependencies.
- Testing injected objects must be easy.
- Catch as much errors as it can.
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

- Services, factories, resources (configuration typically), tags, auto-wiring...
- Dependencies bound through type hints and optionally from variable names
  and/or mapping.
- Integrates well with any code, injected functions can be called as usual
  with all their arguments.
- Thread-safe and limited performance impact (see
  `injection benchmark <https://github.com/Finistere/antidote/blob/master/benchmark.ipynb>`_).
- Dependency cycle detection.
- Easily extendable to support any kind of dependencies.
- Integration with the `attrs <http://www.attrs.org/en/stable/>`_ package
  through the `antidote_attrs` package.


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

    parameters = {
        'db.host': 'host',
        'db.user': 'user',
        'db.port': 5432,
        'db.password': 'password'
    }

    @antidote.resource
    def conf(key):
        return parameters[key]

    # Declare a factory which should be called to instantiate Database.
    # Variables names are used here for injection. A dictionary mapping
    # arguments name to their dependency could also have been used.
    @antidote.factory(dependencies='conf:db.{arg_name}')
    def database_factory(host: str, port: int, user: str, password: str) -> Database:
        """
        Configure your database.
        """
        return Database(
            host=host,
            port=port,
            user=user,
            password=password
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
        host=parameters['db.host'],
        port=parameters['db.port'],
        user=parameters['db.user'],
        password=parameters['db.password']
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
