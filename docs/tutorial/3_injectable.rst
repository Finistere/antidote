3. Injectable
=============


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
