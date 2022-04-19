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

     @injectable                 @inject

          |                         |
          |                         v
    +-----+------+             +----------+
    | Dependency |             | Function |
    +------------+             +----------+

