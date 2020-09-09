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

Antidotes is a declarative dependency injection micro-framework for Python 3.6+
designed for ease of use.


Why Antidote ?
==============

In short antidote avoids you the hassle of instantiating and managing your
services, configuration and so on. You declare them at their definition, and
inject them wherever needed with simple decorators. Now when you only one
service, typically a database, you could handle it through a module acting as a
singleton. But as you start getting more and more services, relying on each other,
you'll start having to maintain code for this, fixing bugs, etc... That's what
Antidote is doing for you.

While there are several dependency injection libraries, there was none which
really convinced me. Most of them did not satisfy all of those requirements:

- Use of type hints: *Be consistent* with type hints as supported by mypy and *use them*
  to inject dependencies. Other means to inject dependencies should be possible.
- Maturity: Support different kind of dependencies and decent tests.
- Easy to integrate with existing code: Introducing a library in a existing application
  shouldn't be a big bang migration whenever possible.
- Not encourage magic: Using the arguments name *implicitly*, by default, to find
  dependencies *is* magic. While magic can make sense in projects, it's rarely a friend
  of maintainability.
- Be nice with developers and their IDE: Use of type hints in the library, no
  :code:`**kwargs` for function arguments (so auto-completion works), should be as easy as
  possible to find definition of dependencies with a right click and "Go to definition",
  etc... This is in the same spirit of avoiding magic.


Features Highlight
==================

Core functionalities:

- Injection of all kinds of functions (method, classmethod, bound or not, ...) through
  type hints and optionally from argument's name and/or with explicitly specified
  dependencies.
- Dependency cycle detection and thread-safety
- Cython implementation, roughly 10x faster the pure Python. With it, Antidote has a
  limited impact on your code:
  `injection benchmark <https://github.com/Finistere/antidote/blob/master/benchmark.ipynb>`_.
- Easily extendable, through dependency providers. All after-mentioned kind of dependencies
  are implemented with it. It is designed to support custom kind of dependencies from the ground up.
  So if you want custom magic or whatever, you can have it !

Kind of dependencies:

- Services and factories: provides an instance of a class.
- Tags: Dependencies can be tagged, and as such all of them matching a specific tag can be
  retrieved.
- Configuration: Constants which are lazily evaluated.
- Definition of interface and services implementing those.


Installation
============

To install Antidote, simply run this command:

.. code-block:: bash

    pip install antidote


Quick Start
===========

How does injection looks like ? Here is a simple example:

.. code-block:: python

   from antidote import inject, register

   # Declare Service as a dependency that can be injected
   @register
   class Service:
       pass

    # uses the type hint
    @inject
    def f(service: Service):
        pass

    f()  # Service will be automatically injected if not provided
    f(Service())  # Want to override injection for tests ? easy

    # Explicitly provide the dependency
    @inject(dependencies=dict(service=Service))
    def f(service):
        pass

    # uses the position of the arguments
    @inject(dependencies=(Service,))
    def f(service):
        pass


Want more ? Here is a more complete example with configurations, services, factories:

.. code-block:: python

    """
    Simple example where a MovieDB interface is defined which can be used
    to retrieve the best movies. In our case the implementation uses IMDB
    to dot it.
    """
    from functools import reduce

    import antidote


    class MovieDB:
        def get_best_movies(self):
            pass


    class ImdbAPI:
        """
        Class from an external library.
        """

        def __init__(self, *args, **kwargs):
            """ Initializes the IMDB API. """


    # Usage of constants for configuration makes refactoring easier and is
    # less error-prone. Moreover Conf will only be instantiated if necessary.
    class Conf(metaclass=antidote.LazyConstantsMeta):
        # The metaclass adds custom behavior for constants (upper case attributes).
        # Conf.IMDB_HOST is a dependency id
        # but Conf().IMDB_HOST is the actual value making it easy to work with.
        IMDB_HOST = 'imdb.host'
        IMDB_API_KEY = 'imdb.api_key'

        def __init__(self):
            # Load configuration from somewhere
            self._raw_conf = {
                'imdb': {
                    'host': 'dummy_host',
                    'api_key': 'dummy_api_key'
                }
            }

        def get(self, key):
            """ 'a.b' -> self._raw_conf['a']['b'] """
            return reduce(dict.get, key.split('.'), self._raw_conf)


    # Declare a factory which should be called to instantiate Database.
    # The order of the arguments is here used to map the dependencies.
    # A dictionary mapping arguments name to their dependency could also
    # have been used.
    @antidote.factory(dependencies=(Conf.IMDB_HOST, Conf.IMDB_API_KEY))
    def imdb_factory(host: str, api_key: str) -> ImdbAPI:
        """
        Configure your database.
        """
        return ImdbAPI(host=host, api_key=api_key)


    # implements specifies that IMDBMovieDB should be used whenever MovieDB is requested.
    @antidote.implements(MovieDB)
    # Registering IMDBMovieDB makes it available in Antidote. (required for @implements)
    @antidote.register
    class IMDBMovieDB(MovieDB):
        # Here the dependencies of __init__() are injected by default as @register treats
        # it as the factory of the service.
        # Note that IMDBMovieDB does not build itself ImdbAPI, which makes testing
        # easier.
        def __init__(self, imdb_api: ImdbAPI):
            self._imdb_api = imdb_api

        def get_best_movies(self):
            pass


    # Inject dependencies in f(), by default only type annotations are used. But
    # arguments name, explicit mapping, etc.. can also be used.
    @antidote.inject
    def f(movie_db: MovieDB):
        """ Do something with your database. """


    # Can be called without arguments now.
    f()

    assert antidote.world.get(MovieDB) is antidote.world.get(IMDBMovieDB)

Looks good, no ? Now you should probably asking yourself, but how do I test all of
that ???

.. code-block:: python

    # You can still explicitly pass the arguments to override
    # injection.
    conf = Conf()
    f(IMDBMovieDB(imdb_factory(
        # equivalent to conf._raw_conf['db.host'], mainly to make your tests easier.
        host=conf.IMDB_HOST,
        api_key=conf._raw_conf['imdb']['api_key'],
    )))

    # Or you can create a new world for your tests
    with world.test.clone():
        f()

        @register
        class DummyService


Interested ? Check out the documentation or try it directly ! There are still features
left such as tags or custom kinds of dependencies.


Cython
======

The cython implementation is roughly 10x faster than the Python one and has strictly the
same API than the pure Python implementation. If you encounter any inconsistencies, please
open an issue !

This also implies that the Cython implementation is _not_ part of the public API, meaning
you cannot rely on it in your own Cython code.

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
