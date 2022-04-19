Use annotated type hints
========================


Antidote supports a variety of annotated type hints which can be used to specify any
existing dependency:

- A :py:class:`.Service` can be retrieved with :py:obj:`.Inject`

    .. testcode:: how_to_annotated_type_hints

        from antidote import injectable, inject, Inject

        @injectable
        class Database:
            pass

        @inject
        def f(db: Inject[Database]) -> Database:
            return db

    .. doctest:: how_to_annotated_type_hints

        >>> f()
        <Database ...>

- A :py:func:`~.factory.factory` and :py:func:`.implementation` can be
  retrieved with :py:class:`.From` or :py:class:`.Get`:

    .. testcode:: how_to_annotated_type_hints

        from antidote import factory, inject, From, Get
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

        @inject
        def g(db: Annotated[Database, Get(Database, source=current_db)]) -> Database:
            return db

    .. doctest:: how_to_annotated_type_hints

        >>> f()
        <Database ...>
        >>> g()
        <Database ...>

- A constant defined with :py:obj:`.const` can be retrieved with :py:class:`.Get`. Actually
  any dependency can be retrieved with it:

    .. testcode:: how_to_annotated_type_hints

        from antidote import const, inject, Get
        from typing import Annotated
        # from typing_extensions import Annotated # Python < 3.9

        class Config:
            HOST = const('localhost')

        @inject
        def f(host: Annotated[str, Get(Config.HOST)]) -> str:
            return host

    .. doctest:: how_to_annotated_type_hints

        >>> f()
        'localhost'

.. note::

    As annotated type hints can quickly become a bit tedious, using type aliases can help:

    .. doctest:: how_to_annotated_type_hints

        >>> CurrentDatabase = Annotated[Database, From(current_db)]
        >>> @inject
        ... def f(db: CurrentDatabase) -> Database:
        ...     return db
        >>> f()
        <Database ...>
