Test in isolation
=================


Testing injected function or class can easily be done by simply specifying manually the
arguments:

.. testcode:: how_to_test

    from antidote import inject, injectable

    @injectable
    class Database:
        pass

    @inject
    def f(db: Database = inject.me()) -> Database:
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
