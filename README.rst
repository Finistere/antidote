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

Antidotes is a declarative dependency injection micro-framework for Python 3.6+. It is designed
on two core ideas:

- Keep dependency declaration close to the actual code as it's deeply related. Dependency injection
  is about removing the responsibility of building dependencies from their clients. Not separating
  how a dependency is built from its implementation.
- It should help creating maintainable code in a straightforward way and offer effortless integration.

Hence it provides the following features:

- Ease of use
    - injection anywhere you need through a decorator `@inject` which uses type hints by default.
    - no \*\*kwargs arguments hiding actual arguments and fully mypy typed, helping you and your IDE.
    - documented, see `<https://antidote.readthedocs.io/en/stable>`_. If you don't find what you need, open an issue ;)
    - thread-safe, cycle detection
    - magic is frowned upon and avoided as much as possible. But it is used when it doesn't hurst
      understandability and improves readability.
- Flexibility
    - A rich ecosystem of dependencies out of the box: services, configuration, factories, interface/implementation, tags.
    - All of those are implemented on top of the core implementation. If Antidote doesn't provide what you need, there's
      a good chance you can implement it yourself quickly.
- Maintainability
    - The different kind of dependencies are designed to be easy to track back. Finding where a
      dependency is defined is easy.
    - Overriding dependencies will raise an exception and one can freeze the dependency space. Once
      frozen, no new dependencies can be defined.
- Testability
    - `@inject` lets you override any injections by passing explicitly the arguments.
    - Override dependencies locally within a context manager. The same is used
      by Antidote itself in most tests.
- Performance
    - Antidote has two implementations: the pure Python one which is the reference and the
      Cython one which is heavily tuned for fast injection. Injection is roughly 10x times faster
      than with the pure Python. It allows using injections without impact on most functions.
      See `injection benchmark <https://github.com/Finistere/antidote/blob/master/benchmark.ipynb>`_


Installation
============

To install Antidote, simply run this command:

.. code-block:: bash

    pip install antidote


Quick Start
===========

How does injection looks like ? Here is a very simple example:

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
    def g(service):
        pass


Want more ? Here is a more complete example with configurations, services, factories:

.. code-block:: python

    """
    Simple example where a MovieDB interface is defined which can be used
    to retrieve the best movies. In our case the implementation uses IMDB
    to dot it.
    """

    from antidote import Constants, factory, Implementation, inject, world

    class MovieDB:
        """ Interface """

        def get_best_movies(self):
            pass

    class ImdbAPI:
        """ Class from an external library. """

        def __init__(self, *args, **kwargs):
            pass

    class Conf(Constants):
        # Configuration values is identified by those class attributes. It helps
        # refactoring as it's easy to find their usage or find their definition.
        # The Constants super class will treat their associated value as the input
        # argument of get(). This allows you to load lazily any configuration.
        IMDB_HOST = 'imdb.host'
        # When used as a dependency, one will have `self.get('imdb.api_key')` injected
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
            """
            self.get('a.b') <=> self._raw_conf['a']['b']
            """
            from functools import reduce
            return reduce(dict.get, key.split('.'), self._raw_conf)

    # ImdbAPI will be provided by this factory, as defined by the return type annotation.
    # The dependencies arguments specifies what must be injected
    @factory(dependencies=(Conf.IMDB_HOST, Conf.IMDB_API_KEY))
    def imdb_factory(host: str, api_key: str) -> ImdbAPI:
        # Here host = Conf().get('imdb.host')
        return ImdbAPI(host=host, api_key=api_key)

    # Implementation tells Antidote that this class should be used as an implementation of
    # the interface MovieDB
    class IMDBMovieDB(MovieDB, Implementation):
        # Antidote specific configuration. By default __init__() is always auto wired,
        # meaning injected. As ImdbAPI is not itself a Service, but is provided by
        # imdb_factory, Antidote requires it to be explicitly stated. This ensures that
        # can always track back where dependencies are coming from.
        __antidote__ = Implementation.Conf().with_wiring(
            dependencies=dict(imdb_api=ImdbAPI @ imdb_factory))

        def __init__(self, imdb_api: ImdbAPI):
            self._imdb_api = imdb_api

        def get_best_movies(self):
            pass

    # Inject dependencies in f(), by default only type annotations are used. But
    # arguments name, explicit mapping, etc.. can also be used.
    @inject
    def f(movie_db: MovieDB):
        pass

    # Can be called without arguments now.
    f()

That looks all good, but what about testability ?

.. code-block:: python

    # You can still explicitly pass the arguments to override
    # injection.
    conf = Conf()
    f(IMDBMovieDB(imdb_factory(
        # The class attributes will retrieve the actual value when called on a instance.
        # Hence this is equivalent to conf.get('imdb.host'), making your tests easier.
        host=conf.IMDB_HOST,
        api_key=conf.IMDB_API_KEY,  # <=> conf.get('imdb.api_key')
    )))

    # Or override dependencies locally within a context manager:
    with world.test.clone(overridable=True):
        world.singletons.add_all({
            Conf.IMDB_HOST: 'other host'
        })
        f()

If you ever need to debug your dependency injections, Antidote also provides a tool to
have a quick summary of what is actually going on. This would be especially helpful if
you encounter cyclic dependencies for example.

.. code-block:: python

    world.debug.tree(f)
    # will output the following:
    """
    f
    └── Static link: MovieDB -> IMDBMovieDB
        └── IMDBMovieDB
            └── ImdbAPI @ imdb_factory
                └── imdb_factory
                    ├── Const: Conf.get('imdb.api_key')
                    │   └── Lazy Conf
                    └── Const: Conf.get('imdb.host')
                        └── Lazy Conf
    """


Hooked ? Check out the documentation ! There are still a lot of features not presented here !


Cython
======

The cython implementation is roughly 10x faster than the Python one and strictly follows the
same API than the pure Python implementation. This implies that you cannot depend on it in your
own Cython code if any. It may be moved to another language.

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
