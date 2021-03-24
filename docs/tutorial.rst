***************
Getting started
***************

This is a beginner friendly tutorial on how to use Antidote.
It is a series of steps to show what can be done easily. Note that Antidote can do a lot
more than presented here, don't hesitate to check out the recipes and references for
more in depth documentation.



1. Introduction
===============


Let's start with a quick example:

.. testcode:: tutorial_overview

    from antidote import inject, world, Provide, Service

    class MyService(Service):
        pass

    @inject
    def f(service: Provide[MyService]):
        # doing stuff
        return service

.. doctest:: tutorial_overview

    >>> f()
    <MyService object at ...>

Now you don't need to provide :code:`MyService` anymore ! Let's start with the basics to
understand what's going on. To simplify a bit, Antidote works this way ::

                 +-----------+
          +----->|   world   +------+
          |      +-----------+      |

     declaration                 @inject

          |                         |
          |                         v
    +-----+------+             +----------+
    | Dependency |             | Function |
    +------------+             +----------+

Dependencies are declared and become part of :py:mod:`.world`. It works somewhat like a
big dictionary of dependencies mapping to their value. From there on you can either
retrieve them yourself or let Antidote inject them for you with :py:func:`.inject`.
By default it'll only rely on annotated type hints (see :py:obj:`typing.Annotated`
and PEP-593). Here we specify with :py:obj:`.Provide` that the type hint itself is the
dependency. Only missing arguments will be injected, hence you can always use the function
normally:

.. doctest:: tutorial_overview

    >>> f(MyService())
    <MyService object at ...>

.. note::

    :py:func:`.inject` is designed to be very flexible. It supports multiple ways to link
    an argument to its dependency if any. You'll encounter some of them later in this
    tutorial, but don't hesitate to check out its documentation by clicking on
    :py:func:`.inject` !

You surely noticed the declaration of :code:`MyService` with:

.. code-block:: python

    class MyService(Service):
        pass

This declares :code:`MyService` as a :py:class:`.Service` just by inheriting it. By default
it will be a singleton. A singleton is a dependency that never changes, it always returns
the same object. :py:func:`.inject` allows us to retrieve it in a function, but you also
can retrieve with :py:func:`.world.get`:

.. doctest:: tutorial_overview

    >>> my_service = world.get(MyService)
    >>> my_service
    <MyService object at ...>

Any dependency can be retrieved with it, not just singletons. Unfortunately, we lost type
information for Mypy and your IDE for auto completion. They both see :code:`my_service` as
an :py:class:`object`. To avoid this, Antidote provides a syntax similar to static languages:

.. doctest:: tutorial_overview

    >>> world.get[MyService](MyService)  # Mypy will understand that this returns a MyService
    <MyService object at ...>
    >>> # As `MyService` is redundant here, you can omit it:
    ... world.get[MyService]()
    <MyService object at ...>

Antidote ensures that the type you specify is valid. A :py:exc:`TypeError` will be raised
otherwise:

.. doctest:: tutorial_overview

    >>> world.get[str](MyService)
    Traceback (most recent call last):
      File "<stdin>", line 1, in ?
    TypeError

.. note::

    While you're free to use :py:func:`.world.get` anywhere you want, better use
    :py:func:`.inject`:

    .. testcode:: tutorial_overview

        @inject
        def good_function(service: Provide[MyService]):
            return service

        def bad_function():
            """
            We're not doing any dependency injection anymore ! We only use Antidote to
            manage dependencies, not more. This makes bad_function() *a lot harder* to
            test !
            """
            service = world.get[MyService]()
            return service

    Furthermore :code:`good_function` is actually faster ! This even more true when using
    the compiled version of Antidote (with Cython), making :code:`good_function` 10x faster.

    The compiled version of Antidote is heavily tuned to have best performance
    with :py:func:`.inject`. You can check whether you're using the compiled version
    with :py:func:`.is_compiled`. Pre-built wheels are only available for Linux currently.



2. Injection
============

Injection is done with the decorator :py:func:`.inject`. By default it relies only on
annotated type hints. Here is are the different ways to use it:

1.  Annotated type hints.

    .. testcode:: tutorial_injection

        from antidote import inject, Service, Provide

        class MyService(Service):
            pass

        @inject
        def f(my_service: Provide[MyService]):
            pass

2.  :code:`dependencies` Defines explicitly which dependency to associate with which
    argument. The most common usage are either with a dictionary:

    .. testcode:: tutorial_injection

        class AnotherService(Service):
            pass

        @inject(dependencies=dict(my_service=MyService, another=AnotherService))
        def f(my_service: MyService, another: AnotherService):
            pass

        # Or more concisely
        @inject(dict(my_service=MyService, another=AnotherService))
        def f(my_service: MyService, another: AnotherService):
            pass

    Or with an iterable of dependencies. In this case the ordering of the dependencies
    is used to

    .. testcode:: tutorial_injection

        # When needed None can be used a placeholder for argument that should be ignored.
        @inject(dependencies=[MyService, AnotherService])
        def f(my_service: MyService, another: AnotherService):
            pass

        # Or more concisely
        @inject([MyService, AnotherService])
        def f(my_service: MyService, another: AnotherService):
            pass

3.  :code:`auto_provide`: When set to :py:obj:`True`, class type hints will be treated
    as dependencies. You can restrict this behavior by specifying a list of classes for
    which it should be used:

    .. testcode:: tutorial_injection

        # Both `my_service` and `another` will be injected
        @inject(auto_provide=True)
        def f(my_service: MyService, another: AnotherService):
            pass

        # argument `another` won't be injected
        @inject(auto_provide=[MyService])
        def f(my_service: MyService, another: AnotherService):
            pass


Antidote will only try to retrieve dependencies for an argument when it's missing. If
found, it'll be injected. If not, a :py:exc:`~.exceptions.DependencyNotFoundError` will
be raised if there is no default argument.



3. Services
===========


We've seend :py:class`.Service` before to declare :code:`MyService` ! Let's take a better
look at it. A service is a class which provides some sort of functionality. A common
example is a class serving as an interface to some external system like a database:

.. testcode:: tutorial_services

    from antidote import inject, Service, Provide

    class Database(Service):
        def __init__(self):
            self.users = [dict(name='Bob')]

    @inject
    def get_user_count(db: Provide[Database]):
        return len(db.users)

    # Or without annotated type hints
    @inject([Database])
    def get_user_count(db: Database):
        return len(db.users)


.. doctest:: tutorial_services

    >>> get_user_count()
    1

By default :py:class:`.Service`\ s are singletons, they are only instantiated once:

.. doctest:: tutorial_services

    >>> from antidote import world
    >>> world.get[Database]() is world.get[Database]()
    True

As services will depend on each other, all methods are wired with :py:func:`.inject`
by default, including :code:`__init__()`. Meaning that you can use annotated type
hints anywhere and they will be taken into account as shown hereafter:

.. testcode:: tutorial_services

    class UserAPI(Service):
        # We didn't need to specify @inject as UserAPI is a Service
        def __init__(self, database: Provide[Database]):
            self.database = database

        def get_user_count(self):
            return len(self.database.users)

.. doctest:: tutorial_services

    >>> from antidote import world
    >>> world.get[UserAPI]().get_user_count()
    1

This simplifies the code as annotated type hints are a good enough indication that
something will be injected.

All those default behaviors can be changed easily with a custom
:py:class:`.Service.Conf` in your :py:class:`.Service`. For example you could create
a non singleton service which uses :code:`auto_provide=True` on all methods by default:

.. testcode:: tutorial_services

    class QueryBuilder(Service):
        __antidote__ = Service.Conf(singleton=False).with_wiring(auto_provide=True)

        def __init__(self, database: Database):
            self.database = database

.. doctest:: tutorial_services

    >>> world.get[QueryBuilder]() is world.get[QueryBuilder]()
    False

You may also find yourself in situations where a single service should be used with
different parameters. For example, a simple service which accumulates metrics
during the application lifetime and flushes it to the database. We could create subclasses
for each possible metric or have one service handle all metrics. But Antidote provides a
nicer way: you to specify constructor arguments when requesting a :py:class:`.Service`:

.. testcode:: tutorial_services

    class MetricAccumulator(Service):
        __antidote__ = Service.Conf(parameters=['name'])

        def __init__(self, name: str, database: Provide[Database]):
            self.name = name
            self._database = database
            self._buffer = []

        @classmethod
        def of(cls, name: str):
            """
            Provides a clean interface with arguments and type hints as parameterized()
            only accepts **kwargs.
            """
            return cls.parameterized(name=name)

        def add(self, value: int):
            self._buffer.append(value)

        def flush(self):
            """flushes buffer to database"""

.. doctest:: tutorial_services

    >>> count_metric = world.get[MetricAccumulator](MetricAccumulator.of('count'))
    >>> count_metric.name
    'count'
    >>> # The same instance is returned because `MetricAccumulator` is defined as a singleton.
    ... count_metric is world.get(MetricAccumulator.of('count'))
    True

When the same arguments are specified, the same service instance will be returned if the
service is defined as a singleton. Simple, yet effective when you need the same service
with different configuration at the same time. With annotated type hints, it would look
like this:


.. testcode:: tutorial_services

    from typing import Annotated
    # from typing_extensions import Annotated # Python < 3.9

    from antidote import Get

    CountMetricAccumulator = Annotated[MetricAccumulator,
                                       Get(MetricAccumulator.of('count'))]

    @inject
    def f(count_metric: CountMetricAccumulator):
        pass

    # Or without annotated type hints. Here we're passing a list of dependencies, so
    # its mapped to the arguments through their position.
    @inject([MetricAccumulator.of('count')])
    def f(count_metric: MetricAccumulator):
        pass

.. note::

    If you cannot inherit from :py:class:`.Service`, you can use the class decorator
    py:func:`.service`:

    .. doctest:: tutorial_services_alternative

        >>> from antidote import service, world
        >>> @service
        ... class Database:
        ...     pass
        >>> world.get[Database]()
        <Database ...>

    However Antidote will only declare as it as a dependency, nothing more. If you want
    some method wiring, check out :py:func:`.wire`.

    You SHOULD ONLY use it to register your own classes. If you want to register external
    classes in Antidote, you should rely on a factory instead presented later.



4. Wiring
=========


When declaring a service with :py:class:`.Service` we've seen that methods, such
as :code:`__init__()` will be automatically wired. Underneath it relies on :py:class:`.Wiring`
which will by default inject all methods. It supports the same arguments as :py:func:`.inject`,
namely :code:`auto_provide` and :code:`dependencies`. Those will be used
for all injected methods. You can also specify explicitly which methods to inject with
:code:`methods`:

.. testcode:: tutorial_wiring

    from antidote import Service, Wiring, Provide

    class Database:
        pass

    class PostgreSQL(Database, Service):
        pass

    class MySQL(Database, Service):
        pass

    class CustomWiring(Service):
        # Only get_host() will be injected. By default, all methods are.
        __antidote__ = Service.Conf(wiring=Wiring(methods=['load_db'],
                                                  auto_provide=[PostgreSQL]))

        def load_db(self, mysql: Provide[MySQL], postgres: PostgreSQL) -> Database:
            return postgres

.. doctest:: tutorial_wiring

    >>> from antidote import world
    >>> world.get[CustomWiring]().load_db()
    <PostgreSQL ...>

If you don't want any wiring at all, you just have to set it to :py:obj:`None`:

.. testcode:: tutorial_wiring

    class NoWiring(Service):
        # No wiring, nothing will be injected not even annotated type hints.
        __antidote__ = Service.Conf(wiring=None)

You can also :py:func:`.inject` to override any :py:class:`.Wiring`:

.. testcode:: tutorial_wiring

    from antidote import inject

    class MultiWiring(Service):
        __antidote__ = Service.Conf(wiring=Wiring(dependencies=dict(db=PostgreSQL)))

        def __init__(self, db: Database):
            self.db = db

        def load_db(self, db: Database) -> Database:
            return db

        # Wiring will not override any injection made explicitly.
        @inject(dict(db=MySQL))
        def load_different_db(self, db: Database) -> Database:
            return db

.. doctest:: tutorial_wiring

    >>> x = world.get[MultiWiring]()
    >>> x.db == x.load_db()
    True
    >>> x.load_different_db()
    <MySQL ...>

For conciseness, Antidote provides some shortcuts:

-   :py:meth:`~.Service.Conf.with_wiring`: allows to keep existing :py:class:`.Wiring`
    configuration and only change some parameters:

    .. testcode:: tutorial_wiring

        class AutoProvidedWiring(Service):
            __antidote__ = Service.Conf().with_wiring(auto_provide=True)

            def __init__(self, db: PostgreSQL):
                self.db = db

    .. doctest:: tutorial_wiring

        >>> world.get[AutoProvidedWiring]().db
        <PostgreSQL ...>

-   If you want to wire classes outside of Antidote, you can use the class decorator
    :py:func:`.wire` which has the same arguments as :py:class:`.Wiring`:

    .. testcode:: tutorial_wiring

        from antidote import wire

        @wire
        class DatabaseUser:
            def load_db(self, db: Provide[PostgreSQL]):
                return db

    .. doctest:: tutorial_wiring

        >>> DatabaseUser().load_db() is world.get[PostgreSQL]()
        True



5. Configuration
================


Antidote :py:class:`.Constants` allows you to define configuration that you can inject
and maintain easily. Like a service where you only need to use "go to definition" to know
how a constant is actually defined. And you know *where* it's used:

.. testcode:: tutorial_conf

    from typing import Annotated
    # from typing_extensions import Annotated # Python < 3.9

    from antidote import Constants, inject, const, Get

    class Config(Constants):
        PORT = const[int](3000)
        DOMAIN = const('example.com')  # type is not required

    @inject
    def absolute_url(path: str,
                     domain: Annotated[str, Get(Config.DOMAIN)],
                     port: Annotated[int, Get(Config.PORT)]):
        return f"https://{domain}:{port}{path}"

    # Or without any annotated type hints.
    # Here None is simply a placeholder, nothing will be injected.
    @inject([None, Config.DOMAIN, Config.PORT])
    def absolute_url(path: str, domain: str, port: int):
        return f"https://{domain}:{port}{path}"

.. doctest:: tutorial_conf

    >>> absolute_url("/user/1")
    'https://example.com:3000/user/1'
    >>> absolute_url('/dog/2', port=80)
    'https://example.com:80/dog/2'
    >>> # For easier testing you can also use a Config instance directly
    ... Config().DOMAIN
    'example.com'

Pretty easy isn't it ? But it feels a bit overkill to just define some constants in Python.
But more often than not your configuration will be coming from a file or even a database.
This can become increasingly complicated if you need to lazily load configuration. Luckily
Antidote forces you to encapsulate how you retrieve the configuration, so it's easy to change:

.. testcode:: tutorial_conf

    class Config(Constants):
        PORT = const[int]('port')
        DOMAIN = const('domain')

        def __init__(self):
            # Load configuration from somewhere. Config will only be instantiated if
            # necessary.
            self._data = dict(domain='example.com', port='80')

        def provide_const(self, name: str, arg: str):
            # Only called when needed.
            return self._data[arg]

.. doctest:: tutorial_conf

    >>> from antidote import world
    >>> world.get(Config.PORT)
    80
    >>> Config().DOMAIN
    'example.com'

You probably noticed that :code:`Config.PORT` we explicitly stated that it was an integer.
it serves several purposes:

-   the actual type of constant value is type checked at runtime.

    .. doctest:: tutorial_conf

        >>> class InvalidConf(Constants):
        ...     WRONG_TYPE = const[Constants]('test')
        >>> InvalidConf().WRONG_TYPE
        Traceback (most recent call last):
          File "<stdin>", line 1, in ?
        TypeError

-   providing a type hint for Mypy:

    .. doctest:: tutorial_conf

        >>> Config().PORT  # treated as an `int` by Mypy
        80
        >>> world.get(Config.PORT)  # same
        80

-   If the type is one of :code:`str`, :code:`float` or :code:`int`, the result of
    :py:meth:`~.Constants.provide_const` will be cast automatically. This allows you to handle
    simply cases where the configuration is retrieved as a string. You can either
    deactivate this behavior or extend it to support enums with
    :py:attr:`~.Constants.Const.auto_cast`.

In the same spirit, :py:func:`.const` allows you to define a default value. It will
only be used if :py:meth:`~.Constants.provide_const` raises a :py:exc:`LookUpError`:

.. testcode:: tutorial_conf

    class Config(Constants):
        PORT = const[int]('port', default=80)
        DOMAIN = const('domain')

        def __init__(self):
            self._data = dict(domain='example.com')

        def provide_const(self, name: str, arg: str):
            return self._data[arg]

.. doctest:: tutorial_conf

    >>> world.get(Config.PORT)
    80
    >>> Config().DOMAIN
    'example.com'



6. Factories & External dependencies
====================================


Factories are ideal to deal with external dependencies which you don't own,
like library classes. The simplest way to declare a factory, is simply to use the function
decorator :py:func:`~.factory.factory`:

.. testcode:: tutorial_factory

    from typing import Annotated
    # from typing_extensions import Annotated # Python < 3.9

    from antidote import factory, inject, From, Constants, const, Get


    class Config(Constants):
        URL = const[str]('localhost:5432')

    # Suppose we don't own the class code, hence we can't define it as a Service
    class Database:
        def __init__(self, url: str):
            self.url = url


    @factory
    def default_db(url: Annotated[str, Get(Config.URL)]) -> Database:
        return Database(url)

    @inject
    def f(db: Annotated[Database, From(default_db)]) -> Database:
        return db

    # Or without annotated type hints
    @factory
    @inject([Config.URL])
    def default_db(url: str) -> Database:
        return Database(url)

    @inject([Database @ default_db])
    def f(db: Database) -> Database:
        return db

.. doctest:: tutorial_factory

    >>> from antidote import world
    >>> f()
    <Database ...>
    >>> world.get[Database](Database @ default_db)
    <Database ...>


The return type MUST always be specified, this is how Antidote knows which dependency you
intend to provide. :py:func:`~.factory.factory` will apply :py:func:`.inject` on the function if not
done already. Hence you can use annotated type hints out of the box but no more without
injecting explicitly. You're probably wondering about the custom syntax when not using
annotated type hints :code:`Database @ default_db`. It provides some very nice properties

- You can trace back how :code:`Database` is instantiated.
- The factory :code:`default_db` will always be loaded by Python before using
  :code:`Database`.

If you need more complex factories, you can use a class instead by inheriting :py:class:`.Factory`:

.. testcode:: tutorial_factory

    from antidote import Factory

    class Database:
        def __init__(self, url: str):
            self.url = url

    class DefaultDB(Factory):
        def __init__(self, url: Annotated[str, Get(Config.URL)]):
            self.url = url

        # Will be called to instantiate Database
        def __call__(self) -> Database:
            return Database(self.url)

:py:class:`.Factory` has more or less the same configuration parameters than :py:class:`.Service`:

- :py:class:`.Factory.Conf` like :py:class:`.Service.Conf`
- :py:meth:`.Factory.parameterized` like :py:meth:`.Service.parameterized`

And you use it the same way as :py:func:`~.factory.factory`:

.. doctest:: tutorial_factory

    >>> world.get[Database](Database @ DefaultDB)
    <Database ...>


7. Tests
========


You've seen until now that Antidote's :py:func:`.inject` does not force you to rely on
the injection to be used:

.. testcode:: tutorial_test

    from antidote import Service, inject, Provide

    class MyService(Service):
        pass

    @inject
    def f(my_service: Provide[MyService]) -> MyService:
        return my_service

    # injected
    f()

    # manual override
    f(MyService())
    f(my_service=MyService())

This allows to test easily individual components in unit-tests easily. But that's not always
enough in more complex tests or integration tests. First of all, let's recap how Antidote
works. In the first section Antidote was roughly described as working as follows::

                 +-----------+
          +----->|   world   +------+
          |      +-----------+      |

     declaration                 @inject

          |                         |
          |                         v
    +-----+------+             +----------+
    | Dependency |             | Function |
    +------------+             +----------+

But that's not really what is happening, in reality we have::

                 +-----------+
                 |   world   |
                 +-----+-----+
                       |
                       +
                    controls
                       +
                       |
                       v
                +------+------+
          +---->+  container  +-----+
          |     +-------------+     |
          +                         +
     declaration                 @inject
          +                         +
          |                         |
    +-----+------+                  v
    | Dependency |             +----+-----+
    +------------+             | Function |
                               +----------+


The container handles all of the state of Antidote such as singletons. The good news is
that :py:mod:`.world` does provide to you the tools to control it in :py:mod:`.world.test`.
Allowing you to override dependencies or test in isolated environments. The most important
one is :py:func:`.world.test.clone`. It'll keep all of your dependency declarations and
isolate you from the outside world:

.. doctest:: tutorial_test

    >>> from antidote import world
    >>> with world.test.clone():
    ...     # This works as expected !
    ...     my_service = f()
    >>> # but it's isolated from the rest, so you don't have the same instance
    ... my_service is world.get(MyService)
    False


It'll also :py:func:`.world.freeze` the local world, meaning that no new dependencies
cannot be added. After all you want to test your existing dependencies not create new ones.

.. doctest:: tutorial_test

    >>> with world.test.clone():
    ...     class NewService(Service):
    ...         pass
    Traceback (most recent call last):
      File "<stdin>", line 1, in ?
    FrozenWorldError

.. note::

    To test new dependencies, you should use :py:func:`.world.test.new` instead:

    .. doctest:: tutorial_test

        >>> with world.test.new():
        ...     class NewService(Service):
        ...         pass
        ...     world.get[NewService]()
        <NewService ...>
        >>> world.get[NewService]()
        Traceback (most recent call last):
          File "<stdin>", line 1, in ?
        DependencyNotFoundError


To change dependencies, you need to use :py:mod:`.world.test.override`:

.. doctest:: tutorial_test

    >>> with world.test.clone():
    ...     world.test.override.singleton(MyService, 'dummy')
    ...     f()
    'dummy'

:py:mod:`.world.test.override` exposes three ways to override dependencies:

-   :py:func:`~.world.test.override.singleton`

    .. doctest:: tutorial_test

        >>> # Use either world.test.override or override directly
        ... from antidote.world.test import override
        >>> with world.test.clone():
        ...     override.singleton(MyService, 'dummy')
        ...     # Can be redefined
        ...     override.singleton(MyService, 'dummy')
        ...     # Multiple dependencies can be declared with a dict
        ...     override.singleton({MyService: 'dummy'})
        ...     f()
        'dummy'

-   :py:func:`~.world.test.override.factory`

    .. doctest:: tutorial_test

        >>> with world.test.clone():
        ...     @override.factory()
        ...     def override_my_service() -> MyService:
        ...         return 'dummy'
        ...     # Can be redefined and will remove any existing instance
        ...     # (if singleton for example)
        ...     @override.factory()
        ...     def override_my_service() -> MyService:
        ...         return 'dummy'
        ...     f()
        'dummy'

-   :py:func:`~.world.test.override.provider`

    .. doctest:: tutorial_test

        >>> from antidote.core import DependencyValue
        >>> with world.test.clone():
        ...     @override.provider()
        ...     def dummy_provider(dependency):
        ...         if dependency is MyService:
        ...             return DependencyValue('dummy')
        ...     f()
        'dummy'

    The decorated function will be called each time a dependency is needed. If it can be
    provided it should be returned wrapped by a :py:class:`~.core.DependencyValue` which also
    defines whether the dependency value is a singleton or not.

    .. warning::

        Beware of :py:func:`~.world.test.override.provider`, it can conflict with
        :py:func:`~.world.test.override.factory` and :py:func:`~.world.test.override.singleton`.
        Dependencies declared with :py:func:`~.world.test.override.singleton` will hide
        :py:func:`~.world.test.override.provider`. And :py:func:`~.world.test.override.provider`
        will hide :py:func:`~.world.test.override.factory`.

        Moreover it won't appear in :py:func:`.world.debug`.

:py:func:`.world.test.clone` will not keep any existing singleton by default, but you may change
it:

.. doctest:: tutorial_test

    >>> my_service = world.get[MyService]()
    >>> with world.test.clone():
    ...     my_service is world.get[MyService]()
    False
    >>> with world.test.clone(keep_singletons=True):
    ...     my_service is world.get[MyService]()
    True

.. warning::

    Beware. keeping singletons will re-use the same object:

    .. doctest:: tutorial_test

        >>> world.get[MyService]().marker = 'marker'
        >>> with world.test.clone(keep_singletons=True):
        ...     world.get[MyService]().marker = 'different'
        >>> world.get[MyService]().marker   # We changed the singleton of the outside world.
        'different'

:py:mod:`.world.test` provides additional utilities when extending Antidote or defining abstract
factories / services.


