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
designed the following ideas:

- Ease of use
    - injection anywhere you need through a decorator `@inject` which uses type hints by default.
    - no \*\*kwargs arguments hiding actual arguments and fully mypy typed, helping you and your IDE.
    - documented with a lot of examples. See `<https://antidote.readthedocs.io/en/stable>`_.
      If you don't find what you need, open an issue ;)
    - thread-safe
- Flexibility
    - A rich ecosystem of dependencies out of the box: services, configuration, factories, interface/implementation, tags.
    - All of those are implemented on top of the core implementation. If Antidote doesn't provide what you need, you can
      add it easily.
- Maintainability
    - The different kind of dependencies are designed to be easy to track back. Finding where a
      dependency is defined is easy.
- Testability
    - `@inject` lets you override any injections by passing explicitly the arguments.
    - you can change any dependency locally within a context manager
- Performance
    - Antidote has two implementations: the pure Python one which is the reference and the
      Cython one which is 10x times faster. With it, injection has a low impact. See
      `injection benchmark <https://github.com/Finistere/antidote/blob/master/benchmark.ipynb>`_


Installation
============

To install Antidote, simply run this command:

.. code-block:: bash

    pip install antidote


Quick Start
===========

How does injection looks like ? Here is a simple example:

.. code-block:: python

   from antidote import inject, Service

   # Declare NyService as a dependency that can be injected
   class MyService(Service):
       pass

    # uses the type hint
    @inject
    def f(service: MyService):
        pass

    f()  # Service will be automatically injected if not provided
    f(MyService())  # but you can still use the function normally

    # There are also different ways to declare which dependency should be used for each
    # arguments, for example: a mapping from arguments to their dependencies
    @inject(dependencies=dict(service=MyService))
    def f(service):
        pass


Want more ? Here is a more complete example with configurations, services, factories:

.. code-block:: python

    """
    Simple example where a MovieDB interface is defined which can be used
    to retrieve the best movies. In our case the implementation uses IMDB
    to dot it.
    """
    import antidote

    # Interface
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
    # less error-prone. Moreover everything is lazy, even the class instantiation.
    # As constants are very similar, this is the only place with some magic to avoid
    # repetition.
    class Conf(antidote.Constants):
        # Constants, by default public upper case attributes, have a special treatment:
        # The class attribute Conf.IMDB_HOST is to be used as a dependency for Antidote
        # but the instance attribute Conf().IMDB_HOST is the actual value allowing some
        # flexibility when testing.

        # 'imdb.host' is not the actual value, it will be given to get() first.
        IMDB_HOST = 'imdb.host'
        IMDB_API_KEY = 'imdb.api_key'

        def __init__(self):
            """ Load configuration from somewhere """
            self._raw_conf = {
                'imdb': {
                    'host': 'dummy_host',
                    'api_key': 'dummy_api_key'
                }
            }

        def get(self, key):
            """ Used to actually retrieve constants.
            self.get('a.b') <=> self._raw_conf['a']['b']
            """
            from functools import reduce
            return reduce(dict.get, key.split('.'), self._raw_conf)


    # Declare a factory which should be called to instantiate Database.
    # The order of the arguments is here used to map the dependencies.
    @antidote.factory(dependencies=(Conf.IMDB_HOST, Conf.IMDB_API_KEY))
    def imdb_factory(host: str, api_key: str) -> ImdbAPI:
        """
        Configure your database.
        """
        return ImdbAPI(host=host, api_key=api_key)


    # implements specifies that IMDBMovieDB should be used whenever MovieDB is requested.
    @antidote.implements(MovieDB)
    # Declaring IMDBMovieDB as a Service which makes it available for Antidote
    class IMDBMovieDB(MovieDB, antidote.Service):
        # Services have __init__() automatically injected (auto-wiring).
        # Note here a custom syntax for the ImdbAPI provided by imdb_factory. This has
        # the nice advantage of enforcing imdb_factory to declared before and it is now
        # easy to track back what's going on !
        def __init__(self, imdb_api: ImdbAPI @ imdb_factory):
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

That looks all good, but what about testability ?

.. code-block:: python

    # You can still explicitly pass the arguments to override
    # injection.
    conf = Conf()
    f(IMDBMovieDB(imdb_factory(
        # equivalent to conf._raw_conf['db.host'], mainly to make your tests easier.
        host=conf.IMDB_HOST,
        api_key=conf._raw_conf['imdb']['api_key'],
    )))

    # Or modify dependencies within a test:
    with antidote.world.test.clone(overridable=True):
        antidote.world.singletons.add_all({
            Conf.IMDB_HOST: 'other host'
        })
        f()


Hooked ? Check out the documentation ! There are still a lot of features not presented here !


Cython
======

The cython implementation is roughly 10x faster than the Python one and has strictly the
same API than the pure Python implementation. This also implies that the Cython implementation
is _not_ part of the public API, meaning you cannot rely on it in your own Cython code.

If you encounter any inconsistencies, please open an issue !
You use the pure python with the following:

.. code-block:: bash

    pip install --no-binary antidote

Note that it will nonetheless try to compile with Cython if available.


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

If you have any issue during development or just want some feedback, don't hesitate
to open a pull request and ask for help !

Pull requests **will not** be accepted if:

- classes and non trivial functions have not docstrings documenting their behavior.
- tests do not cover all of code changes (100% coverage).
