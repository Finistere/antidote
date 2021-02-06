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


Antidotes is a dependency injection micro-framework for Python 3.6+. The core idea
is ensuring best *maintainability* while avoiding the need of declaring dependencies in a
separate file. Dependency injection is about removing the responsibility of building
dependencies from their clients. It does not imply that dependency management should
be done in a separate file.

It provides the following features:

- Ease of use
    - injection anywhere you need through a decorator :code:`@inject`, be it static methods, functions, etc..
      By default, it will only rely on annotated type hints, but it supports a lot more!
    - no \*\*kwargs arguments hiding actual arguments and fully mypy typed, helping you and your IDE.
    - `documented <https://antidote.readthedocs.io/en/stable>`_, everything has working examples.
    - thread-safe, cycle detection.
- Flexibility
    - Most common dependencies out of the box: services, configuration, factories, interface/implementation.
    - All of those are implemented on top of the core implementation. If Antidote doesn't provide what you need, there's
      a good chance you can implement it yourself.
    - scope support
    - async injection
- Maintainability
    - All dependencies can be tracked back to their declaration/implementation easily.
    - Mypy compatibility and usage of type hints as much as possible.
    - Overriding dependencies will raise an error outside of tests.
    - Dependencies can be frozen, which blocks any new definitions.
    - No double injection.
    - :code:`@inject` does not inject anything implicitly.
    - type checks when a type is explicitly defined with :code:`world.get`, :code:`world.lazy` and constants.
- Testability
    - :code:`@inject` lets you override any injections by passing explicitly the arguments.
    - Override locally in a test any dependency.
    - When encountering issues you can retrieve the full dependency tree, nicely formatted, with `world.debug`.
- Performance
    - Antidote has two implementations: the pure Python one which is the reference and the
      compiled one (cython) which is heavily tuned for fast injection. The compiled version is the fastest dependency
      injection library.
      See `comparison benchmark <https://github.com/Finistere/antidote/blob/master/comparison.ipynb>`_ and
      `antidote benchmark <https://github.com/Finistere/antidote/blob/master/benchmark.ipynb>`_.

.. image:: docs/_static/img/comparison_benchmark.png
    :alt: Comparison benchmark image


Installation
============

To install Antidote, simply run this command:

.. code-block:: bash

    pip install antidote


Documentation
=============

Beginner friendly tutorial, recipes and the reference can be found in the ` documentation <https://antidote.readthedocs.io/en/stable>`_.


Hands-on quick start
====================

Short and concise example of some of the most important features of Antidote.

How does injection looks like ? Here is a simple example:

.. code-block:: python

    from antidote import inject, Service, Constants, const, world, Provide, Get
    from typing import Annotated
    # from typing_extensions import Annotated # Python < 3.9

    class Conf(Constants):
        DB_HOST = const[str]('localhost:5432')
        DB_HOST_WITHOUT_TYPE_HINT = const('localhost:5432')

    # Declared as a Service
    class Database(Service):
        # All methods are decorated with @inject by default
        def __init__(self, host: Annotated[str, Get(Conf.DB_HOST)]):
            self._host = host

    @inject  # Uses only annotated type hints by default
    def f(db: Provide[Database] = None):
        # Used to tell Mypy that `db` is optional but must be either injected or given.
        assert db is not None
        pass

    f()  # yeah !
    f(Database('localhost:5432'))  # override injection

    # You can also retrieve dependencies by hand
    world.get(Conf.DB_HOST)
    world.get[str](Conf.DB_HOST)  # with type hint
    # if the dependency is the type itself, you may omit it:
    world.get[Database]()


Or without annotated type hints (PEP-593):

.. code-block:: python

    class Database(Service):
        @inject({'host': Conf.DB_HOST})
        def __init__(self, host: str):
            self._host = host

    @inject([Database])
    def f(db: Database = None):
        assert db is not None
        pass

    # auto_provide => Class type hints are treated as dependencies.
    @inject(auto_provide=True)
    def f(db: Database = None):
        assert db is not None
        pass


Want more ? Here is an over-engineered example to showcase a lot more features:

.. code-block:: python

    # Some library.py
    class ImdbAPI:
        def __init__(self, host: str, port: int, api_key: str):
            pass

.. code-block:: python

    # The interface exposed in your code
    class MovieDB:
        def get_best_movies():
            pass

    # Code using MovieDB
    @inject
    def f(movie_db: Annotated[MovieDB, From(current_movie_db)] = None):
        assert movie_db is not None  # for Mypy
        pass

    f()


Now searching for the definition of :code:`current_movie_db` would lead you to:

.. code-block:: python

    # Code implementing/managing MovieDB
    from antidote import (Constants, factory, inject, world, const, Service,
                          implementation, Get, From)
    from typing import Annotated
    # from typing_extensions import Annotated # Python < 3.9

    class Conf(Constants):
        # with str/int/float, the type hint is enforced. Can be removed or extend to
        # support Enums.
        IMDB_HOST = const[str]('imdb.host')
        IMDB_PORT = const[int]('imdb.port')
        IMDB_API_KEY = const('imdb.api_key')

        def __init__(self):
            """
            Load configuration from somewhere. You can change how you configure your
            application later, it won't impact the whole application.
            """
            self._raw_conf = {
                'imdb': {
                    'host': 'dummy_host',
                    'api_key': 'dummy_api_key',
                    'port': '80'
                }
            }

        def provide_const(self, name: str, arg: str):
            root, key = arg.split('.')
            return self._raw_const[root][key]

    # Provides ImdbAPI, as defined by the return type annotation.
    @factory
    def imdb_factory(host: Annotated[str, Get(Conf.IMDB_HOST)],
                     port: Annotated[int, Get(Conf.IMDB_PORT)],
                     api_key: Annotated[str, Get(Conf.IMDB_API_KEY)]
                     ) -> ImdbAPI:
        # Here host = Conf().get('imdb.host')
        return ImdbAPI(host=host, port=port, api_key=api_key)

    class IMDBMovieDB(MovieDB, Service):
        __antidote__ = Service.Conf(singleton=False)  # New instance each time

        def __init__(self, imdb_api: Annotated[ImdbAPI, From(imdb_factory)]):
            self._imdb_api = imdb_api

        def get_best_movies():
            pass

    @implementation(MovieDB)
    def current_movie_db():
        return IMDBMovieDB  # dependency to be provided for MovieDB


Or without annotated type hints:

.. code-block:: python

    @factory
    @inject([Conf.IMDB_HOST, Conf.IMDB_PORT, Conf.IMDB_API_KEY])
    def imdb_factory(host: str, port: int, api_key: str) -> ImdbAPI:
        return ImdbAPI(host, port, api_key)

    class IMDBMovieDB(MovieDB, Service):
        __antidote__ = Service.Conf(singleton=False)

        @inject({'imdb_api': ImdbAPI @ imdb_factory})
        def __init__(self, imdb_api: ImdbAPI):
            self._imdb_api = imdb_api

    @inject([MovieDB @ current_movie_db])
    def f(movie_db: MovieDB = None):
        assert movie_db is not None
        pass


We've seen that you can override any parameter:

.. code-block:: python

    conf = Conf()
    f(IMDBMovieDB(imdb_factory(
        # constants can be retrieved directly on an instance
        host=conf.IMDB_HOST,
        port=conf.IMDB_PORT,
        api_key=conf.IMDB_API_KEY,
    )))

But if you only to change one part in a complex dependency graph, you can override them
locally with:

.. code-block:: python

    # Override locally some dependencies:
    with world.test.clone(keep_singletons=True):
        world.test.override.singleton(Conf.IMDB_HOST, 'other host')
        f()

If you ever need to debug your dependency injections, Antidote also provides a tool to
have a quick summary of what is actually going on:

.. code-block:: python

    world.debug(f)
    # will output:
    """
    f
    └── Permanent implementation: MovieDB @ current_movie_db
        └──<∅> IMDBMovieDB
            └── ImdbAPI @ imdb_factory
                └── imdb_factory
                    ├── Const: Conf.IMDB_API_KEY
                    │   └── Conf
                    │       └── Singleton: 'conf_path' -> '/etc/app.conf'
                    ├── Const: Conf.IMDB_PORT
                    │   └── Conf
                    │       └── Singleton: 'conf_path' -> '/etc/app.conf'
                    └── Const: Conf.IMDB_HOST
                        └── Conf
                            └── Singleton: 'conf_path' -> '/etc/app.conf'

    Singletons have no scope markers.
    <∅> = no scope (new instance each time)
    <name> = custom scope
    """


Hooked ? Check out the `documentation <https://antidote.readthedocs.io/en/stable>`_ !
There are still features not presented here !


Comparison
==========

*Disclaimer: This comparison is mostly based on the documentation of the most popular libraries I know of, not less not more.*

Why choose Antidote ?

- **Everything is explicit**: Some libraries using an :code:`@inject`-like decorator, such as injector_, lagom_ or python_inject_ will
  instantiate any missing arguments. Antidote will only inject dependencies
  that you have defined as such and only when told so. Making it easier to understand what is injected or not at first glance.
- **Flexibility**: With the exception of dependency_injector_, most libraries will only support services (class), simple factories and singletons.
  Antidote also provides configuration, interfaces, stateful factories, lazy methods/functions, scopes, async injection.
- **Maintainability**: Again with the exception of dependency_injector_, dependency injection libraries can make it difficult to
  understand how/where a dependency is created. Typically when declaring a factory for a service (class), you won't have any way
  of finding easily the function when using the service. Antidote syntax *always* ensures that you can. Antidote primary
  goal is helping you create maintainable code.
- **Performance**: Antidote's :code:`@inject` is heavily tuned for performance in the compiled version (Cython). No other
  library goes as far. Now whether it's really useful for a dependency injection library is debatable. But this allows
  you to use :code:`@inject` virtually anywhere without any impact. (See benchmarks on the top)

The main difference with dependency_injector_ is the philosophy of the library. With dependency_injector_ declaration of
dependencies to the :code:`container` and their implementation are in two separate files:

.. code-block:: python

    # my_service.py
    # Dependency Injector
    class MyService:
        pass

.. code-block:: python

    # services.py
    # Dependency Injector
    from dependency_injector import containers, providers

    class Container(containers.DeclarativeContainer):
        my_service = providers.Singleton(MyService)


This implies that you have one more file to maintain. And with a lot of dependencies you start managing either
one big container or multiple ones.

However this one big advantage compared to most other dependency injection libraries: it's easy to understand how
dependencies are wired together, making it a lot more maintainable than most libraries. It is especially visible
when declaring factories. With dependency_injector_ you would do something like that:

.. code-block:: python

    # services.py
    # Dependency Injector
    class Container(containers.DeclarativeContainer):
        my_service = providers.Factory(my_factory)

While most other libraries you have no easy way to know how :code:`MyService` is created by the dependency injection
framework:

.. code-block:: python

    # services.py
    # Injector
    @provider
    def my_factory() -> MyService:
        pass

    @inject
    def f(s: MyService):
        pass

    # Lagom
    container[MyService] = my_factory

    @magic_bind_to_container(container)
    def f(s: MyService):
        pass

    # Python Inject
    def config(binder):
        binder.bind(MyService, my_factory)

    inject.configure(config)

    @inject.autoparams()
    def f(s: MyService):
        pass

But with Antidote you can **always** track back to the definition of a dependency:

.. code-block:: python

    from antidote import factory, inject, From

    @factory
    def my_factory() -> MyService:
        pass

    @inject(dict(my_service=MyService @ my_factory))
    def f(my_service: MyService):
        pass

    # Or with annotated type hints
    @inject
    def f(my_service: Annotated[MyService, From(my_factory)]):
        pass


IMHO, this makes Antidote on of the, if not the, most maintainable dependency injection library. There is
no container to manage and you can always understand the wiring easily.

.. _dependency_injector: https://python-dependency-injector.ets-labs.org/introduction/di_in_python.html
.. _pinject: https://github.com/google/pinject
.. _injector: https://github.com/alecthomas/injector
.. _python_inject: https://github.com/ivankorobkov/python-inject
.. _lagom: https://github.com/meadsteve/lagom


Cython
======

The cython implementation is roughly 10x faster than the Python one and strictly follows the
same API than the pure Python implementation. This implies that you cannot depend on it in your
own Cython code if any. It isn't part of the public API.

If you encounter any inconsistencies, please open an issue !
You can avoid the Cython version from PyPI with the following:

.. code-block:: bash

    pip install --no-binary antidote

Beware that PyPy is only tested with the pure Python version, not the Cython one.


Issues / Feature Requests / Questions
=====================================

Feel free to open an issue on Github for questions, requests or issues ! ;)


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
- tests do not cover all of code changes (100% coverage) in the pure python.

If you face issues with the Cython part of Antidote just send the pull request, I can
adapt the Cython part myself.
