******
How to
******



Be compatible with Mypy
=======================


Antidote passes the strict Mypy check and exposes its type information (PEP 561).
Unfortunately static typing for decorators is limited to simple cases, hence Antidote :code:`@inject` will just
return the same signature from Mypys point of view. The best way, currently that I know of, is to
define arguments as optional as shown below:

.. testcode:: how_to_mypy

    from antidote import inject, Service, Provide

    class MyService(Service):
        pass

    @inject
    def f(my_service: Provide[MyService] = None) -> MyService:
        # We never expect it to be None, but it Mypy will now
        # understand that my_service may not be provided.
        assert my_service is not None
        return my_service


    s: MyService = f()

    # You can also overload the function, if you want a more accurate type definition:
    from typing import overload

    @overload
    def g(my_service: MyService) -> MyService: ...

    @overload
    def g() -> MyService: ...

    @inject
    def g(my_service: Provide[MyService] = None) -> MyService:
        assert my_service is not None
        return my_service


    s2: MyService = g()


Note that any of this is only necessary if you're calling _explicitly_ the function, if only
instantiate :code:`MyService` through Antidote for example, you won't need this for its
:code:`__init__()` function typically. You could also use a :code:`Protocol` to define
a different signature, but it's more complex.



Use annotated type hints
========================


Antidote supports a variety of annotated type hints which can be used to specify any
existing dependency:

- A :py:class:`.Service` can be retrieved with :py:obj:`.Provide`

    .. testcode:: how_to_annotated_type_hints

        from antidote import Service, inject, Provide

        class Database(Service):
            pass

        @inject
        def f(db: Provide[Database]) -> Database:
            return db

    .. doctest:: how_to_annotated_type_hints

        >>> f()
        <Database ...>

- A :py:class:`.Factory`, :py:func:`~.factory.factory` and :py:func:`.implementation` can be
  retrieved with :py:class:`.From`:

    .. testcode:: how_to_annotated_type_hints

        from antidote import factory, inject, From
        from typing import Annotated
        # from typing_extensions import Annotated # Python < 3.9

        class Database:
            pass

        @factory
        def current_db() -> Database:
            return Database()

        @inject
        def f(db: Annotated[Database, From(current_db)]) -> Database:
            return db

    .. doctest:: how_to_annotated_type_hints

        >>> f()
        <Database ...>

- A constant from :py:class:`.Constants` can be retrieved with :py:class:`.Get`. Actually
  any dependency can be retrieved with it:

    .. testcode:: how_to_annotated_type_hints

        from antidote import Constants, const, inject, Get
        from typing import Annotated
        # from typing_extensions import Annotated # Python < 3.9

        class Config(Constants):
            HOST = const('localhost')

        @inject
        def f(host: Annotated[str, Get(Config.HOST)]) -> str:
            return host

    .. doctest:: how_to_annotated_type_hints

        >>> f()
        'localhost'

There is also :py:class:`.FromArg` which allows you to use information on the argument
itself to decide what should be injected. The same can be done without annotated type hints
with the arguments :code:`dependencies` of :py:func:`.inject`.



Test in isolation
=================


Testing injected function or class can easily be done by simply specifying manually the
arguments:

.. testcode:: how_to_test

    from antidote import Service, inject, Provide

    class Database(Service):
        pass

    @inject
    def f(db: Provide[Database]) -> Database:
        return db

.. doctest:: how_to_test

    >>> f()
    <Database ...>
    >>> class TestDatabase:
    ...     pass
    >>> f(TestDatabase())
    <TestDatabase ...>

This works well for unit tests, but less for integration or functional tests. So Antidote
can isolate your tests with :py:func:`.world.test.clone`. Inside you'll have access to
any existing dependency, but their value will be different.

.. doctest:: how_to_test

    >>> from antidote import world
    >>> real_db = world.get[Database]()
    >>> with world.test.clone():
    ...     world.get[Database]() is real_db
    False

You can also override them easily with:

- :py:func:`.world.test.override.singleton`

    .. doctest:: how_to_test

        >>> with world.test.clone():
        ...     world.test.override.singleton(Database, "fake database")
        ...     world.get(Database)
        'fake database'

- :py:func:`.world.test.override.factory`

    .. doctest:: how_to_test

        >>> with world.test.clone():
        ...     @world.test.override.factory()
        ...     def local_db() -> Database:
        ...         return "fake database"
        ...     # Or
        ...     @world.test.override.factory(Database)
        ...     def local_db():
        ...         return "fake database"
        ...
        ...     world.get(Database)
        'fake database'

You can override as many times as you want:

.. doctest:: how_to_test

    >>> with world.test.clone():
    ...     world.test.override.singleton(Database, "fake database 1 ")
    ...     @world.test.override.factory(Database)
    ...     def local_db():
    ...         return "fake database 2"
    ...
    ...     world.test.override.singleton(Database, "fake database 3")
    ...     world.get(Database)
    'fake database 3'

.. note::

    :py:func:`.world.test.clone` will :py:func:`~.world.freeze` the cloned world, meaning
    no new dependencies can be defined.

All of the above should be what you need 99% of the time.

There is also a "joker" override
:py:func:`.world.test.override.provider` which allows more complex overrides. But I do
**NOT recommend** its usage unless your absolutely have to. It can conflict with other
overrides and will not appear in :py:func:`.world.debug`.



Debug dependency issues
=======================


If you encounter dependency issues or cycles, you can take a look at the whole dependency
tree with :py:func:`.world.debug`:

.. testcode:: how_to_debug

    from antidote import world, Service, inject, Provide

    class MyService(Service):
        pass

    @inject
    def f(s: Provide[MyService]):
        pass

    print(world.debug(f))

It will output:

.. testoutput:: how_to_debug
    :options: +NORMALIZE_WHITESPACE

    f
    └── MyService

    Singletons have no scope markers.
    <∅> = no scope (new instance each time)
    <name> = custom scope


.. note::

    If you're not using scopes, you only need to remember that :code:`<∅>` is equivalent
    to :code:`singleton=False`.


Now wit the more complex example presented in the home page of Antidote we have:

.. code-block:: text

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


If you ever encounter a cyclic dependency, it will be present with a:

.. code-block:: text

    /!\\ Cyclic dependency: X

Ambiguous dependencies, which cannot be identified uniquely through their name, such as tags,
will have their id added to help differentiate them:

.. testcode:: how_to_debug

    from antidote import LazyCall

    def current_status():
        pass

    STATUS = LazyCall(current_status)

    print(world.debug(STATUS))

will output the following

.. testoutput:: how_to_debug
    :options: +NORMALIZE_WHITESPACE

    Lazy: current_status()  #...

    Singletons have no scope markers.
    <∅> = no scope (new instance each time)
    <name> = custom scope

.. code-block:: text

    Lazy: current_status()  #0P2QAw

    Singletons have no scope markers.
    <∅> = no scope (new instance each time)
    <name> = custom scope
