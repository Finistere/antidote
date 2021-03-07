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


Antidotes is a dependency injection micro-framework for Python 3.6+. It is built on the
idea of ensuring best **maintainability** of your code while being as **easy to use** as possible.
It also provides the **fastest** injection with :code:`@inject` allowing you to use it virtually anywhere.

Antidote provides the following features:

- Ease of use
    - Injection anywhere you need through a decorator :code:`@inject`, be it static methods, functions, etc..
      By default, it will only rely on annotated type hints, but it supports a lot more!
    - No :code:`**kwargs` arguments hiding actual arguments and fully mypy typed, helping you and your IDE.
    - `Documented <https://antidote.readthedocs.io/en/latest>`_, everything has tested examples.
    - No need for any custom setup, just use your injected function as usual. You just don't have to specify injected arguments anymore.
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
    - Dependencies can be frozen, which blocks any new declarations.
    - No double injection.
    - Everything is as explicit as possible, :code:`@inject` does not inject anything implicitly.
    - type checks when a type is explicitly defined with :code:`world.get`, :code:`world.lazy` and constants.
    - thread-safe, cycle detection.
- Testability
    - fully isolate all the dependencies of each test.
    - :code:`@inject` lets you override any injections by passing explicitly the arguments.
    - Override locally in a test any dependency.
    - When encountering issues you can retrieve the full dependency tree, nicely formatted, with :code:`world.debug`.
- Performance\*
    - fastest :code:`@inject` with heavily tuned Cython.
    - testing utilities are tuned to ensure that even with full isolation it stays fast.
    - benchmarks:
      `comparison <https://github.com/Finistere/antidote/blob/master/comparison.ipynb>`_,
      `injection <https://github.com/Finistere/antidote/blob/master/benchmark.ipynb>`_,
      `test utilities <https://github.com/Finistere/antidote/blob/master/benchmark_test_utils.ipynb>`_

*\*with the compiled version, in Cython. Pre-built wheels for Linux. See further down for more details.*

.. image:: docs/_static/img/comparison_benchmark.png
    :alt: Comparison benchmark image



Installation
============

To install Antidote, simply run this command:

.. code-block:: bash

    pip install antidote


Documentation
=============

Beginner friendly tutorial, recipes, the reference and a FAQ can be found in the
`documentation <https://antidote.readthedocs.io/en/latest>`_.

Here are some links:

- `Why dependency injection ? <https://antidote.readthedocs.io/en/latest/faq.html#why-dependency-injection>`_
- `Why use a dependency injection framework ? <https://antidote.readthedocs.io/en/latest/faq.html#why-use-a-dependency-injection-framework>`_
- `Why choose Antidote ? <https://antidote.readthedocs.io/en/latest/faq.html#why-choose-antidote>`_
- `Getting Started <https://antidote.readthedocs.io/en/latest/tutorial.html#getting-started>`_
- `Changelog <https://antidote.readthedocs.io/en/latest/changelog.html>`_


Issues / Feature Requests / Questions
=====================================

Feel free to open an issue on Github for questions, requests or issues !


Hands-on quick start
====================

Showcase of the most important features of Antidote with short and concise examples.
Checkout the `Getting started`_ for a full beginner friendly tutorial.

A simple service
----------------

How does injection looks like ? Here is a simple example:

.. code-block:: python

    from antidote import inject, Service, Constants, const, world

    class Conf(Constants):
        DB_HOST = const('localhost:5432')

    class Database(Service):
        @inject([Conf.DB_HOST])  # based on argument position
        def __init__(self, host: str):
            self._host = host

    @inject({'db': Database})
    def f(db: Database):
        pass

    f()  # yeah !
    f(Database('localhost:5432'))  # override injection

    # Retrieve dependencies by hand, in tests typically
    world.get(Conf.DB_HOST)
    world.get[str](Conf.DB_HOST)  # with type hint
    world.get[Database]()  # omit dependency if it's the type hint itself


Or with annotated type hints (PEP-593):

.. code-block:: python

    from typing import Annotated
    # from typing_extensions import Annotated # Python < 3.9
    from antidote import Get, Provide

    class Database(Service):
        # All methods are decorated with @inject by default
        def __init__(self, host: Annotated[str, Get(Conf.DB_HOST)]):
            self._host = host

    @inject
    def f(db: Provide[Database]):
        pass

Or with :code:`auto_provide`:

.. code-block:: python

    # auto_provide => Class type hints are treated as dependencies.
    @inject(auto_provide=True)
    def f(db: Database):
        pass

If you want to be compatible with Mypy type checking, you just need to do the following:

.. code-block:: python

    @inject
    def f(db: Provide[Database] = None):
        # Used to tell Mypy that `db` is optional but must be either injected or given.
        assert db is not None
        pass

This might look a bit cumbersome, but in reality you'll only need to do it in functions
you are actually calling yourself in your code. Typically :code:`Database.__init__()`
won't need it because it'll always be Antidote injecting the arguments.

A more complex case
-------------------

Want more ? Here is an over-engineered example to showcase a lot more features. First we have
an :code:`ImdbAPI` coming from a external library:

.. code-block:: python

    # from a library
    class ImdbAPI:
        def __init__(self, host: str, port: int, api_key: str):
            pass


You have your own interface to manipulate the movies:

.. code-block:: python

    # movie.py
    class MovieDB:
        """ Interface """

        def get_best_movies(self):
            pass


Now that's the entry point of your application:

.. code-block:: python

    # main.py
    from movie import MovieDB
    from current_movie import current_movie_db


    @inject([MovieDB @ current_movie_db])
    def main(movie_db: MovieDB = None):
        assert movie_db is not None  # for Mypy, to understand that movie_db is optional
        pass

    # Or with annotated type hints
    @inject
    def main(movie_db: Annotated[MovieDB, From(current_movie_db)]):
        pass

    if __name__ == '__main__':
        main()


Note that you can search for the definition of :code:`current_movie_db`. So you can simply
use "Go to definition" of your IDE which would open:

.. code-block:: python

    # current_movie.py
    # Code implementing/managing MovieDB
    from antidote import factory, inject, Service, implementation
    from config import Config

    # Provides ImdbAPI, as defined by the return type annotation.
    @factory
    @inject([Config.IMDB_HOST, Config.IMDB_PORT, Config.IMDB_API_KEY])
    def imdb_factory(host: str, port: int, api_key: str) -> ImdbAPI:
        # Here host = Config().provide_const('IMDB_HOST', 'imdb.host')
        return ImdbAPI(host=host, port=port, api_key=api_key)

    class IMDBMovieDB(MovieDB, Service):
        __antidote__ = Service.Conf(singleton=False)  # New instance each time

        @inject({'imdb_api': ImdbAPI @ imdb_factory})
        def __init__(self, imdb_api: ImdbAPI):
            self._imdb_api = imdb_api

        def get_best_movies(self):
            pass

    @implementation(MovieDB)
    def current_movie_db() -> object:
        return IMDBMovieDB  # dependency to be provided for MovieDB


Or with annotated type hints:

.. code-block:: python

    # current_movie.py
    # Code implementing/managing MovieDB
    from antidote import factory, Service, Get, From
    from typing import Annotated
    # from typing_extensions import Annotated # Python < 3.9
    from config import Config

    @factory
    def imdb_factory(host: Annotated[str, Get(Config.IMDB_HOST)],
                     port: Annotated[int, Get(Config.IMDB_PORT)],
                     api_key: Annotated[str, Get(Config.IMDB_API_KEY)]
                     ) -> ImdbAPI:
        return ImdbAPI(host, port, api_key)

    class IMDBMovieDB(MovieDB, Service):
        __antidote__ = Service.Conf(singleton=False)

        def __init__(self, imdb_api: Annotated[ImdbAPI, From(imdb_factory)]):
            self._imdb_api = imdb_api

        def get_best_movies(self):
            pass


The configuration can also be easily tracked down:

.. code-block:: python

    # config.py
    from antidote import Constants, const

    class Config(Constants):
        # with str/int/float, the type hint is enforced. Can be removed or extend to
        # support Enums.
        IMDB_HOST = const[str]('imdb.host')
        IMDB_PORT = const[int]('imdb.port')
        IMDB_API_KEY = const('imdb.api_key')

        def __init__(self):
            self._raw_conf = {
                'imdb': {
                    'host': 'dummy_host',
                    'api_key': 'dummy_api_key',
                    'port': '80'
                }
            }

        def provide_const(self, name: str, arg: str):
            root, key = arg.split('.')
            return self._raw_conf[root][key]

Now you can override any of the arguments, typically in tests:

.. code-block:: python

    conf = Config()
    main(IMDBMovieDB(imdb_factory(
        # constants can be retrieved directly on an instance
        host=conf.IMDB_HOST,
        port=conf.IMDB_PORT,
        api_key=conf.IMDB_API_KEY,
    )))

You can also fully isolate your tests from each other while relying on Antidote and
override any dependencies within that context:

.. code-block:: python

    from antidote import world

    # Clone current world to isolate it from the rest
    with world.test.clone():
        # Override the configuration
        world.test.override.singleton(Config.IMDB_HOST, 'other host')
        main()

If you ever need to debug your dependency injections, Antidote also provides a tool to
have a quick summary of what is actually going on:

.. code-block:: python

    world.debug(main)
    # will output:
    """
    main
    └── Permanent implementation: MovieDB @ current_movie_db
        └──<∅> IMDBMovieDB
            └── ImdbAPI @ imdb_factory
                └── imdb_factory
                    ├── Const: Config.IMDB_API_KEY
                    │   └── Config
                    ├── Const: Config.IMDB_PORT
                    │   └── Config
                    └── Const: Config.IMDB_HOST
                        └── Config

    Singletons have no scope markers.
    <∅> = no scope (new instance each time)
    <name> = custom scope
    """


Hooked ? Check out the `documentation <https://antidote.readthedocs.io/en/latest>`_ !
There are still features not presented here !


Compiled
========

The compiled implementation is roughly 10x faster than the Python one and strictly follows the
same API than the pure Python implementation. Pre-compiled wheels are available only for Linux currently.
You can check whether you're using the compiled version or not with:

.. code-block:: python

    from antidote import is_compiled
    
    print(f"Is Antidote compiled ? {is_compiled()}")

You can force the compilation of antidote yourself when installing:

.. code-block:: bash

    ANTIDOTE_COMPILED=true pip install antidote
    
On the contrary, you can force the pure Python version with:

.. code-block:: bash

    pip install --no-binary antidote

.. note::

    The compiled version is not tested against PyPy. The compiled version relies currently on Cython,
    but it is not part of the public API. Relying on it in your own Cython code is at your risk.


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
