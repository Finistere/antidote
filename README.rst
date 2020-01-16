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
- Avoids as much magic as possible. Finding the source and the usage of a dependency
  is straightforward (through an IDE's "Go to definition" / "Find usage").
- Core functionality is flexible and extendable to support any custom injection/dependencies.
  So while Antidote does not use magic, you can.
- Limit performance impact of injection.
- Provide a rich set of ways for handling dependencies. (factories, tags,
  interfaces, configuration, etc...).
- Handle all the different edge cases with methods, bound methods, class methods, etc...


Why Dependency Injection ?
==========================

In short antidote avoids you the hassle of instantiating and managing your
services. You declare them at their definition, and inject them wherever
needed with simple decorators, which
*do not change how you interact with your objects*. Unit testing is not
impacted as one can override any injection and control the available
dependencies easily.

For the longer version: `<https://antidote.readthedocs.io/en/stable/why.html>`_


Why Antidote ?
==============

While there are several dependency injection libraries, there was none which
really convinced me. Most of them did not satisfy all of those requirements:

- Use of type hints: *Be consistent* with type hints as supported by mypy and *use them*
  to inject dependencies. Other means to inject dependencies should be possible.
- Maturity: Support different kind of dependencies, proper test coverage,
- Easy to integrate with existing code: Ideally it means just adding decorators to
  your class/functions and that's it.
- Avoid magic: It should be straightforward for someone, unaware of the dependency
  injection library, to know what is injected and from where it comes. Typically using
  the arguments name implicitly to find dependencies *is* magic. How can you know from
  where it comes ? Hence type hints are for example a lot better.

And for the rare ones that were close to those requirements, I didn't like their API for
different reasons. Which is obviously a matter of taste.


Features Highlight
==================

Core functionalities:

- Injection done through type hints and optionally from argument's name and/or
  with explicitly specified dependencies.
- Dependency cycle detection
- Thread-safety and limited performace impact (see
  `injection benchmark <https://github.com/Finistere/antidote/blob/master/benchmark.ipynb>`_).
- Antidote is declarative and does not do any magic out of the box. Reading the decorators
  is enough to understand what it does and from where dependencies are coming from.
- Is easy to work with an IDE: no :code:`**kwargs` which makes arguments impossible to guess and
  has type hints everywhere.
- Easily extendable, through dependency providers. All after-mentioned kind of dependencies
  are implemented with it. It is designed to support custom kind of dependencies from the ground up.
  So if you want custom magic or whatever, you can have it !

Kind of dependencies:

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

    # You can still explicitly pass the arguments to override
    # injection.
    conf = Conf()
    f(IMDBMovieDB(imdb_factory(
        # equivalent to conf._raw_conf['db.host'], mainly to make your tests easier.
        host=conf.IMDB_HOST,
        api_key=conf._raw_conf['imdb']['api_key'],
    )))


Interested ? Check out the documentation or try it directly ! There are still features
left such as tags or custom kinds of dependencies.


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
