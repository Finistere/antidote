*******
Recipes
*******


This is a collection of how to use certain features of Antidote or simply examples of
what can be done.



Use interfaces
==============


Antidote supports the distinction interface/implementation out of the box with the
function decorator :py:func:`~.implementation`. The result of the function will be the
retrieved dependency for the specified interface. Typically this means a class registered
as a service or one that can be provided by a factory.

.. testcode:: recipes_interface_implementation

    from antidote import implementation, service, inject, Constants, const

    class Database:
        pass

    @service
    class PostgresDB(Database):
        pass

    @service
    class MySQLDB(Database):
        pass

    class Conf(Constants):
        DB_CONN_STR = const[str]('postgres:...')

    # permanent is True by default. If you want to choose on each call which implementation
    # should be used, set it to False.
    @implementation(Database, permanent=True)
    def local_db(db_conn_str: str = Conf.DB_CONN_STR) -> object:
        db, *rest = db_conn_str.split(':')
        if db == 'postgres':
            # Complex dependencies are supported
            return PostgresDB
        elif db == 'mysql':
            # But you can also simply return the class
            return MySQLDB
        else:
            raise RuntimeError(f"{db} is not a supported database")


Similar to a :py:func:`~.factory.factory` you must specify the source of the dependency:

.. doctest:: recipes_interface_implementation

    >>> @inject
    ... def f(db: Database = inject.me(source=local_db)):
    ...     return db
    >>> f()
    <PostgresDB ...>
    >>> from antidote import world
    >>> world.get(Database, source=local_db)
    <PostgresDB ...>



Lazily call a function
======================


Calling lazily a function can be done with :py:class:`.lazy` or
:py:class:`.LazyMethodCall` for methods. Both will pass any arguments passed on
and can either be singletons or not.


Function
--------

.. testsetup:: recipes_lazy

    import sys

    class DummyRequests:
        def get(url):
            return url

    sys.modules['requests'] = DummyRequests()

.. testcode:: recipes_lazy

    import requests
    from antidote import LazyCall, inject

    def fetch_remote_conf(name):
        return requests.get(f"https://example.com/conf/{name}")

    CONF_A = LazyCall(fetch_remote_conf)("conf_a")

    @inject(dependencies=(CONF_A,))
    def f(conf):
        return conf

Using :code:`CONF_A` as a representation of the result allows one to easily identify
where this dependency is needed. Moreover neither :code:`f` nor its caller needs to
be aware on how to call :code:`fetch_remote_conf`.


Method
------

Lazily calling a method requires the class to be :py:class:`.Service`.

.. testcode:: recipes_lazy

    from antidote import LazyMethodCall, service

    @service
    class ExampleCom:
        def get(url):
            return requests.get(f"https://example.com{url}")

        STATUS = LazyMethodCall(get, singleton=False)("/status")

.. note::

    If you intend to define lazy constants, consider using
    :py:class:`.Constants` instead.



Create a stateful factory
=========================


Antidote supports stateful factories simply by using defining a class as a factory:

.. testcode:: recipes_stateful_factory

    from antidote import factory

    class ID:
        def __init__(self, id: str):
            self.id = id

        def __repr__(self):
            return "ID(id='{}')".format(self.id)

    @factory(singleton=False)
    class IDFactory:
        def __init__(self, id_prefix: str = "example"):
            self._prefix = id_prefix
            self._next = 1

        def __call__(self) -> ID:
            id = ID("{}_{}".format(self._prefix, self._next))
            self._next += 1
            return id

.. doctest:: recipes_stateful_factory

    >>> from antidote import world
    >>> world.get(ID, source=IDFactory)
    ID(id='example_1')
    >>> world.get(ID, source=IDFactory)
    ID(id='example_2')


In this example we choose to inject :code:`id_prefix` in the :code:`__init__()`, but we
also could have done it in the :code:`__call__()`. Both are injected by default, but they
have different use cases. The factory itself is always a singleton, so static dependencies
should be injected through :code:`__init__()`. If you need dependencies that changes, get
them through :code:`__call__()`. Obviously you can change that behavior through the
:py:class:`.Factory.Conf`: defined in :code:`__antidote__`.


.. note::

    Stateful factories can also be used to provide dependencies that have a more complex
    scope than Antidote provides (singleton or not). Although, if you need to handle some
    scope for multiples dependencies it might be worth just extending Antidote through a
    :py:class:`.Provider`.



Configuration
=============

Here are some examples on how to use :py:class:`.Constants` to handle configuration coming
from different sources.


From the environment
--------------------

.. testcode:: recipes_configuration_environment

    import os
    from typing import Optional
    from antidote import Constants, const

    class Env(Constants):
        SECRET = const[str]()

        def provide_const(self, name: str, arg: Optional[object]):
            return os.environ[name]

.. doctest:: recipes_configuration_environment

    >>> from antidote import world, inject
    >>> os.environ['SECRET'] = 'my_secret'
    >>> world.get[str](Env.SECRET)
    'my_secret'
    >>> @inject
    ... def f(secret: str = Env.SECRET) -> str:
    ...     return secret
    >>> f()
    'my_secret'



From a dictionary
-----------------

Configuration can be stored in a lot of different formats, or even be retrieved on a
remote endpoint at start-up. Most of the time you would be able to easily convert it
to a dictionary and use the following:

.. testcode:: recipes_configuration_dictionary

    import os
    from typing import Optional
    from antidote import Constants, const

    class Conf(Constants):
        HOST = const[str]('host')
        AWS_API_KEY = const[str]('aws.api_key')

        def __init__(self):
            # Load your configuration into a dictionary
            self._raw_conf = {
                "host": "localhost",
                "aws": {
                    "api_key": "my key"
                }
            }

        def provide_const(self, name: str, arg: Optional[str]):
            from functools import reduce

            assert arg is not None and isinstance(arg, str)  # sanity check
            return reduce(dict.get, arg.split('.'), self._raw_conf)  # type: ignore

.. doctest:: recipes_configuration_dictionary

    >>> from antidote import world, inject
    >>> world.get[str](Conf.HOST)
    'localhost'
    >>> world.get(Conf.AWS_API_KEY)
    'my key'
    >>> @inject
    ... def f(key: str = Conf.AWS_API_KEY) -> str:
    ...     return key
    >>> f()
    'my key'


Specifying a type / Using Enums
-------------------------------

You can specify a type when using :py:func:`.const`. It's main purpose is to provide
a type for Mypy when the constants are directly accessed from an instance. However
:py:class:`.Constants` will also automatically force the cast  if the type is one
of :code:`str`, :code:`float` or :code:`int`. You can control this behavior with
the :code:`auto_cast` argument of :py:attr:`~.Constants.Conf`. A typical use case
would be to support enums as presented here:


.. testcode:: recipes_configuration_auto_cast

    from enum import Enum
    from typing import Optional
    from antidote import Constants, const

    class Env(Enum):
        PROD = 'prod'
        PREPRDO = 'preprod'

    class Conf(Constants):
        __antidote__ = Constants.Conf(auto_cast=[int, Env])

        DB_PORT = const[int]()
        ENV = const[Env]()

        def provide_const(self, name: str, arg: Optional[object]):
            return {'db_port': '5432', 'env': 'prod'}[name.lower()]


.. doctest:: recipes_configuration_auto_cast

    >>> from antidote import world, inject
    >>> Conf().DB_PORT
    5432
    >>> Conf().ENV
    <Env.PROD: 'prod'>
    >>> world.get[int](Conf.DB_PORT)
    5432
    >>> world.get[Env](Conf.ENV)
    <Env.PROD: 'prod'>
    >>> @inject
    ... def f(env: Env = Conf.ENV) -> Env:
    ...     return env
    >>> f()
    <Env.PROD: 'prod'>


The goal of this is to simplify common operations when manipulating the environment
or configuration files. If you need complex behavior, consider using a service for this
or define your Configuration class as :code:`public=True` in :py:attr:`~.Constants.Conf`
and use it as a one.


Default values
--------------

Default values can be specified in :py:func:`.const`:

.. testcode:: recipes_configuration_default

    import os
    from antidote import Constants, const

    class Env(Constants):
        HOST = const[str]('HOST', default='localhost')

        def get(self, value):
            return os.environ[value]

It will be use if :code:`get` raises a py:exec:`KeyError`. For more complex behavior,
using a :py:class:`collections.ChainMap` which loads your defaults and the user is a good
alternative:

.. testcode:: recipes_configuration_default

    from collections import ChainMap
    from antidote import Constants, const

    class Configuration(Constants):
        def __init__(self):
            user_conf = dict()  # load conf from a file, etc..
            default_conf = dict()
            # User conf will override default_conf
            self._raw_conf = ChainMap(user_conf, default_conf)

An alternative to this would be using a configuration format that supports overrides, such
as HOCON.



Scopes
======

.. _recipes-scopes:

A dependency may be associated with a scope. If so it'll cached for as along as the scope is
valid. The most common scope being the singleton scope where dependencies are cached forever.
When the scope is set to :py:obj:`None`, the dependency value will be retrieved each time.
Scopes can be create through :py:func:`.world.scopes.new`. The name is only used to
have a friendly identifier when debugging.

.. doctest:: recipes_scope

    >>> from antidote import world
    >>> REQUEST_SCOPE = world.scopes.new(name='request')

To use the newly created scope, use :code:`scope` parameters:

.. doctest:: recipes_scope

    >>> from antidote import service
    >>> @service(scope=REQUEST_SCOPE)
    ... class Dummy:
    ...     pass

As :code:`Dummy` has been defined with a custom scope, the dependency value will
be kep as long as :code:`REQUEST_SCOPE` stays valid. That is to say, until you reset
it with :py:func:`.world.scopes.reset`:

.. doctest:: recipes_scope

    >>> current = world.get(Dummy)
    >>> current is world.get(Dummy)
    True
    >>> world.scopes.reset(REQUEST_SCOPE)
    >>> current is world.get(Dummy)
    False

In a Flask app for example you would then just reset the scope after each request:


.. code-block:: python

    from flask import Flask

    app = Flask(__name__)

    @app.after_request
    def reset_request_scope():
        world.scopes.reset(REQUEST_SCOPE)

