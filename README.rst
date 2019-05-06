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


Hereafter is an example which tries to show most of Antidote's features:


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
        # Dependencies of __init__() are injected by default when
        # registering a service.
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

    # You can still explicitly pass the arguments to override
    # injection.
    conf = Conf()
    f(IMDBMovieDB(imdb_factory(
        # equivalent to conf._raw_conf['db.host'], mainly to make your tests easier.
        host=conf.IMDB_HOST,
        api_key=conf._raw_conf['imdb']['api_key'],
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
