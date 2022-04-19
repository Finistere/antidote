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
