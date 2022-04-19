***************
Getting started
***************

This is a beginner friendly tutorial on how to use Antidote.
It is a series of steps to show what can be done easily. Note that Antidote can do a lot
more than presented here, don't hesitate to check out the recipes and references for
more in depth documentation.



1. Introduction
===============


Let's start with the basics and define a simple class that can be injected, an :py:func:`.injectable`:

.. testcode:: tutorial_overview

    from antidote import inject, injectable

    @injectable
    class Database:
        ...

    @inject
    def load_database(db: Database = inject.me()) -> Database:
        # doing stuff
        return db

Now you don't need to provide :code:`Database` to :code:`do_stuff()` anymore!

.. doctest:: tutorial_overview

    >>> load_database()
    <Database object at ...>

By default :py:func:`.injectable` declares singletons, meaning there's only one instance of
:code:`Database`:

.. doctest:: tutorial_overview

    >>> load_database() is load_database()
    True

You can override the injected dependency explicitly, which is particularly useful for testing:

.. doctest:: tutorial_overview

    >>> load_database(Database())
    <Database object at ...>

.. note::

    Antidote provides more advanced testing mechanism which are presented in a later section.

Lastly but not the least, :py:obj:`.world.get` can also retrieve dependencies:

.. doctest:: tutorial_overview

    >>> from antidote import world
    >>> world.get(Database)
    <Database object at ...>

Mypy will usually be able to correctly infer the typing. But, if you find yourself in a corner case,
you can use the alternative syntax to provide type information:

.. doctest:: tutorial_overview

    >>> # Specifying the return type explicitly
    ... world.get[Database](Database)
    <Database object at ...>

Antidote will enforce the type when possible, if the provided type information is really a type.

.. note::

    Prefer using :py:func:`.inject` to :py:obj:`.world.get`:

    .. testcode:: tutorial_overview

        @inject
        def good(db: Database = inject.me()):
            return db

        def bad():
            db = world.get(Database)
            return db

    .. testcleanup:: tutorial_overview

        good()
        bad()

    :code:`bad` does not rely on dependency injection making it harder to test! :py:func:`.inject` is
    also considerably faster thanks to heavily tuned cython code.


But how does Antidote work underneath ? To simplify a bit, Antidote can be summarized as single
catalog of dependencies :py:mod:`.world`. Decorators like :py:func:`.injectable` declares dependencies
and :py:obj:`.inject` retrieves them::

                 +-----------+
          +----->|   world   +------+
          |      +-----------+      |

       @injectable                  @inject

          |                         |
          |                         v
    +-----+------+             +----------+
    | Dependency |             | Function |
    +------------+             +----------+



2. Injection
============


As seen before :py:func:`.inject` is used to inject dependencies in functions. There are multiple
ways to define the dependencies to be injected. Most of them will be used in this tutorial. The priority is defined as such:

.. testcode:: tutorial_injection

    from antidote import inject, injectable

    @injectable
    class Database:
        ...

    @injectable
    class Cache:
        ...


1.  Markers which replace the default value:, such as :py:meth:`.Inject.me` or :py:meth:`.Inject.get`:

    .. testcode:: tutorial_injection

        @inject
        def f(db: Database = inject.me()):
            ...

        @inject
        def f2(db = inject.get(Database)):
            ...

    .. testcleanup:: tutorial_injection

        f()
        f2()

1.  Annotated type hints as defined by PEP-593. It cannot be used with markers on the same argument.

    .. testcode:: tutorial_injection

        from antidote import Inject

        @inject
        def f(db: Inject[Database]):
            ...

    .. testcleanup:: tutorial_injection

        f()

2.  :code:`dependencies` Defines explicitly which dependency to associate with which
    argument:

    .. testcode:: tutorial_injection

        @inject(dependencies=dict(db=Database, cache=Cache))
        def f(db: Database, cache: Cache):
            ...

        # To ignore one argument use `None` as a placeholder.
        @inject(dependencies=[Database, Cache])
        def f2(db: Database, cache: Cache):
            ...

        # Or more concisely
        @inject({'db': Database, 'cache': Cache})
        def f3(db: Database, cache: Cache):
            ...

        @inject([Database, Cache])
        def f4(db: Database, cache: Cache):
            ...

    .. testcleanup:: tutorial_injection

        f()
        f2()
        f3()
        f4()


Antidote will only inject dependencies for *missing* arguments. If not possible, a :py:exc:`~.exceptions.DependencyNotFoundError` is raised.
The only exception is the :py:meth:`.Inject.me` marker which will provide :py:obj:`None` if the argument is :code:`Optional`:

.. doctest:: tutorial_injection

    >>> from typing import Optional
    >>> class Dummy:
    ...     ...
    >>> @inject
    ... def f(dummy: Optional[Dummy] = inject.me()) -> Optional[Dummy]:
    ...     return dummy
    >>> f() is None
    True


3. Injectables
==============


Any class decorated with `@injectable` can be provided by Antidote:.

.. testcode:: tutorial_injectables

    from antidote import injectable

    @injectable
    class Database:
        ...

.. doctest:: tutorial_injectables
    :hide:

    >>> from antidote import world
    >>> world.get(Database)
    <Database object at ...>
    >>> world.get(Database) is world.get(Database)
    True

By default it's a singleton, so only one instance will exist. This behavior can be controlled with:

.. testcode:: tutorial_injectables

    @injectable(singleton=False)
    class Database:
        ...

.. doctest:: tutorial_injectables
    :hide:

    >>> from antidote import world
    >>> world.get(Database)
    <Database object at ...>
    >>> world.get(Database) is not world.get(Database)
    True

On top of declaring the dependency, :py:func:`.injectable` also wires the class and so injects all
methods by default:

.. testcode:: tutorial_injectables

    from antidote import inject

    @injectable
    class AuthenticationService:
        def __init__(self, db: Database = inject.me()):
            self.db = db

.. doctest:: tutorial_injectables

    >>> from antidote import world
    >>> world.get(AuthenticationService).db
    <Database object at ...>

You can customize injection by applying a custom :py:func:`.inject` on methods:

.. testcode:: tutorial_injectables

    @injectable
    class AuthenticationService:
        @inject({'db': Database})
        def __init__(self, db: Database):
            self.db = db

.. doctest:: tutorial_injectables
    :hide:

    >>> from antidote import world
    >>> world.get(AuthenticationService).db
    <Database object at ...>


or by specifying your
own :py:class:`.Wiring`.

.. testcode:: tutorial_injectables

    from antidote import Wiring

    @injectable(wiring=Wiring(methods=['__init__']))
    class AuthenticationService:
        def __init__(self, db: Database = inject.me()):
            self.db = db

.. doctest:: tutorial_injectables
    :hide:

    >>> from antidote import world
    >>> world.get(AuthenticationService).db
    <Database object at ...>

.. note::

    This class wiring behavior can be used through :py:func:`.wire`, it isn't specific to
    :py:func:`.injectable`.

You can also specify a factory method to control to have fine control over the instantiation:

.. testcode:: tutorial_injectables

    from __future__ import annotations


    @injectable(factory_method='build')
    class AuthenticationService:
        @classmethod
        def build(cls) -> AuthenticationService:
            return cls()

.. doctest:: tutorial_injectables
    :hide:

    >>> from antidote import world
    >>> world.get(AuthenticationService)
    <AuthenticationService object at ...>


One last point, :py:func:`.injectable` is best used on your own classes. If you want to register
external classes in Antidote, you should rely on a :py:func:`~.factory.factory` instead presented
in a later section.



4. Configuration
================


Configuration, or more generally constants, can be found in any application. Antidote provides
a simple abstraction layer :py:class:`.Constants` which allows you to re-define later *how* you
retrieve those constants without breaking your users:

.. testcode:: tutorial_conf

    from antidote import Constants, inject, const

    class Config(Constants):
        PORT = const(3000)
        DOMAIN = const('example.com')

    @inject
    def absolute_url(path: str,
                     domain: str = Config.DOMAIN,
                     port: int = Config.PORT
                     ) -> str:
        return f"https://{domain}:{port}{path}"


.. doctest:: tutorial_conf

    >>> absolute_url("/user/1")
    'https://example.com:3000/user/1'
    >>> absolute_url('/dog/2', port=80)
    'https://example.com:80/dog/2'

Both :code:`PORT` and :code:`DOMAIN` have different behavior whether they're used from the class or
from an instance:

- From the class, it's a dependency and a marker. So you can use it directly with :py:func:`.inject`
  as shown before and you can retrieve it from :py:obj:`.world`:

    .. doctest:: tutorial_conf

        >>> from antidote import world
        >>> world.get[str](Config.DOMAIN)
        'example.com'

- From an instance, it'll retrieve the actual value which makes testing the class a lot easier:

    .. doctest:: tutorial_conf

        >>> Config().DOMAIN
        'example.com'

Now :py:class:`.Constants` really shines when your constants aren't hard-coded. The class will
be lazily instantiated and you can customize how constants are actually retrieved:

.. testcode:: tutorial_conf

    from typing import Optional

    class Config(Constants):
        PORT = const('serving_port')
        DOMAIN = const()

        # Lazy loading of your configuration
        def __init__(self):
            self._data = dict(domain='example.com', serving_port=80)

        def provide_const(self,
                          name: str,  # name of the const(), ex: "DOMAIN"
                          arg: Optional[str]  # argument given to const() if any, None otherwise.
                          ) -> object:
            if arg is None:
                return self._data[name.lower()]
            return self._data[arg]

:py:func:`.const` also provides two additional features:

- A default value can be provided which will be used on :py:exc:`LookUpError`\s.

    .. testcode:: tutorial_conf

        class Config(Constants):
            PORT = const(default=80)

            def provide_const(self, name: str, arg: Optional[object]) -> object:
                raise LookupError(name)

    .. doctest:: tutorial_conf

        >>> Config().PORT
        80

- type enforcement:

    .. testcode:: tutorial_conf

        class Config(Constants):
            PORT = const[int](object())
            DOMAIN = const[str]('example.com')

    .. doctest:: tutorial_conf

        >>> Config().DOMAIN
        'example.com'
        >>> Config().PORT
        Traceback (most recent call last):
          File "<stdin>", line 1, in ?
        TypeError: ...


:py:class:`.Constants` can even go a step further by not only enforcing types but also casting the
value:

.. testcode:: tutorial_conf

    class Config(Constants):
        PORT = const[int]('80')

.. doctest:: tutorial_conf

    >>> Config().PORT
    80

This only works on primitive types out of the box: :code:`int`, :code:`float` and :code:`str`. You
can other types like this:


.. testcode:: tutorial_conf

    from enum import Enum

    class Env(Enum):
        PROD = 'prod'
        DEV = 'dev'

    class Config(Constants):
        __antidote__ = Constants.Conf(auto_cast=[int, Env])
        PORT = const[int]('80')
        ENV = const[Env]('dev')

.. doctest:: tutorial_conf

    >>> Config().PORT
    80
    >>> Config().ENV
    <Env.DEV: 'dev'>



6. Factories & External dependencies
====================================


Factories are ideal to deal with external dependencies which you don't own,
like library classes. The simplest way to declare a factory, is simply to use the
decorator :py:func:`~.factory.factory`:

.. testsetup:: tutorial_factory

    class Database:
        def __init__(self, *args, **kwargs) -> None:
            pass

.. testcode:: tutorial_factory

    from antidote import factory, inject, Constants, const
    # from my_favorite_library import Database

    class Config(Constants):
        URL = const[str]('localhost:5432')


    @factory
    def default_db(url: str = Config.URL) -> Database:  # @factory applies @inject automatically
        return Database(url)


    @inject
    def f(db: Database = inject.me(source=default_db)) -> Database:
        return db


.. doctest:: tutorial_factory

    >>> from antidote import world
    >>> f()
    <Database ...>
    >>> world.get(Database, source=default_db)
    <Database ...>

:py:func:`~.factory.factory` will automatically use :py:func:`.inject` which lets us use markers
and annotation for dependency injection of the factory itself. You can still apply
:py:func:`.inject` yourself for total control or even disable the auto-wiring.

You probably noticed how Antidote forces you to specify the factory when using it for dependency
injection! There are two reasons for it:

- You can trace back how :code:`Database` is instantiated.
- The factory :code:`default_db` will always be loaded by Python before using
  :code:`Database`.

Antidote will enforce that the specified factory and class are consistent, relying on the return
type of the factory:

.. doctest:: tutorial_factory

    >>> class Dummy:
    ...     pass
    >>> world.get(Dummy, source=default_db)
    Traceback (most recent call last):
      File "<stdin>", line 1, in ?
    TypeError: ...

For more complex factories, you can use a class factory:

.. testcode:: tutorial_factory

    @factory
    class DefaultDB:
        def __init__(self, url: str = Config.URL):
            self.url = url

        # Will be called to instantiate Database
        def __call__(self) -> Database:
            return Database(self.url)


7. Tests
========


Until now, you've seen that you could still use normally injected functions:

.. testcode:: tutorial_test

    from antidote import injectable, inject

    @injectable
    class MyService:
        pass

    @inject
    def f(my_service: MyService = inject.me()) -> MyService:
        return my_service

    # injected
    f()

    # manual override
    f(MyService())
    f(my_service=MyService())

This allows to test easily individual components in unit-tests. But in more complex tests it's usually
not enough. So Antidote provides additional tooling to isolate tests and change dependencies. The most
important of them is :py:func:`world.test.clone`. It'll create an isolated world with the same
dependencies declaration, but not the same instances!

.. doctest:: tutorial_test

    >>> from antidote import world
    >>> with world.test.clone():
    ...     # This works as expected !
    ...     my_service = f()
    >>> # but it's isolated from the rest, so you don't have the same instance
    ... my_service is world.get(MyService)
    False
    >>> dummy = object()
    >>> with world.test.clone():
    ...     # Override dependencies however you like
    ...     world.test.override.singleton(MyService, dummy)
    ...     f() is dummy
    True

You can also use a factory to override dependencies:

.. doctest:: tutorial_test

    >>> with world.test.clone():
    ...     @world.test.override.factory()
    ...     def override_my_service() -> MyService:
    ...         return dummy
    ...     f() is dummy
    True

Overrides can be changed at will and override each other. You can also nest test worlds and keep
the singletons you defined:


.. doctest:: tutorial_test

    >>> with world.test.clone():
    ...     world.test.override.singleton(MyService, dummy)
    ...     # override twice MyService
    ...     world.test.override.singleton(MyService, dummy)
    ...     with world.test.clone():
    ...         f() is dummy
    False
    >>> with world.test.clone():
    ...     world.test.override.singleton(MyService, dummy)
    ...     with world.test.clone(keep_singletons=True):
    ...         f() is dummy
    True


Beware that :py:func:`world.test.clone` will automatically :py:func:`.world.freeze`: no new dependencies
cannot be defined. After all you want to test your existing dependencies not create new ones.

.. doctest:: tutorial_test

    >>> with world.test.clone():
    ...     @injectable
    ...     class NewService:
    ...         pass
    Traceback (most recent call last):
      File "<stdin>", line 1, in ?
    FrozenWorldError

To test new dependencies, you should use :py:func:`.world.test.new` instead:

.. doctest:: tutorial_test

    >>> with world.test.new():
    ...     @injectable
    ...     class NewService:
    ...         pass
    ...     world.get(NewService)
    <NewService ...>
    >>> world.get[NewService]()
    Traceback (most recent call last):
      File "<stdin>", line 1, in ?
    DependencyNotFoundError
