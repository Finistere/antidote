Recipes
=======


This is a collection of how to use certain features of Antidote or simply examples of
what can be done.


Use interfaces
--------------

Antidote supports the distinction interface/implementation out of the box. The
implementation needs to be retrievable and hence typically defined as a
:py:class:`~.Service`.

When the choice of the implementation is straightforward you can simply use
:py:func:`~.implements`: :

.. testcode:: how_to_interface_implements

    from antidote import Service, implements

    class Interface:
        pass

    @implements(Interface)
    class MyService(Service, Interface):
        pass

.. doctest:: how_to_interface_implements

    >>> from antidote import world
    >>> world.get[Interface]()
    <MyService ...>

If you have multiple possible implementation you'll need to rely on the function decorator
:py:func:`~.implementation`. The result of the function will be the retrieved dependency
for the specified interface. Typically this means a class registered as a service or one
that can be provided by a factory.

.. testcode:: how_to_interface_implementation

    from antidote import implementation, Service, inject

    class Database:
        def __init__(self, host: str, name: str):
            self.host = host
            self.name = name

    class PostgresDB(Service, Database):
        pass

    class MySQLDB(Service, Database):
        pass

    # permanent is True by default. If you want to choose each time which implementation
    # should be used, set it to False.
    @implementation(Database, permanent=True, dependencies=['db_conn_str'])
    def choose_db(conn_str):
        db, host, name = conn_str.split(':')
        if db == 'postgres':
            # Complex dependencies are supported
            return PostgresDB.with_kwargs(host=host, name=name)
        elif db == 'mysql':
            # But you can also simply return the class
            return MySQLDB
        else:
            raise RuntimeError(f"{db} is not a supported database")


.. doctest:: how_to_interface_implementation

    >>> from antidote import world
    >>> world.singletons.set('db_conn_str', 'postgres:localhost:my_project')
    >>> db = world.get[Database]()
    >>> db
    <PostgresDB ...>
    >>> db.host
    'localhost'
    >>> db.name
    'my_project'


.. note::

    You may wonder why one needs to specify the interface in :py:func:`~.implements`,
    as here the interface is obvious. There are two reasons for this:

    - Multiple and/or deep inheritance chain would otherwise make it ambiguous
      to know which interface is used by Antidote.
    - While it isn't perfect, you can easily find which services are used by
      Antidote by searching :code:`@implements(Interface` through your code.


Lazily call a function
----------------------

Calling lazily a function can be done with :py:class:`.LazyCall` or
:py:class:`.LazyMethodCall` for methods. Both will pass any arguments passed on
and can either be singletons or not.

Function call
^^^^^^^^^^^^^

.. testsetup:: how_to_lazy

    import sys

    class DummyRequests:
        def get(url):
            return url

    sys.modules['requests'] = DummyRequests()

.. testcode:: how_to_lazy

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

Method call
^^^^^^^^^^^

.. testcode:: how_to_lazy

    from antidote import LazyMethodCall, Service

    class ExampleCom(Service):
        def get(url):
            return requests.get(f"https://example.com{url}")

        STATUS = LazyMethodCall(get, singleton=False)("/status")

Lazily calling a method through :py:class:`.LazyMethodCall` requires the class
to be defined as a service. The class itself will only be instantiated when
necessary.

.. note::

    If you intend to define multiple constants lazily, consider using
    :py:class:`.Constants` instead.


Use tags to retrieve multiple dependencies
------------------------------------------

Tags are a way to retrieve a list of services, such as plugins, extensions, etc... In
Antidote tags are instance of :py:class:`.Tag`. Dependencies tagged with this instance
can simply be retrieved by requesting this specific tag from Antidote. You'll get a
:py:class:`.Tagged` instances containing both your dependencies and their associated
instance of :py:class:`.Tag`.

.. testcode:: how_to_tags

    from antidote import Service, Tag

    tag = Tag()

    class PluginA(Service):
        __antidote__ = Service.Conf(tags=[tag])

    class PluginB(Service):
        __antidote__ = Service.Conf(tags=[tag])

.. doctest:: how_to_tags

    >>> from antidote import world, Tagged
    >>> tagged = world.get[Tagged](tag)
    >>> list(sorted(tagged.values(), key=lambda plugin: type(plugin).__name__))
    [<PluginA ...>, <PluginB ...>]

You can do more than that with tags though, you can

- store information in them.
- change how dependencies are grouped.

To do so, just create your own subclass:

.. testcode:: how_to_tags

    class CustomTag(Tag):
        __slots__ = ('name',)  # __slots__ isn't required
        name: str  # For Mypy

        def __init__(self, name: str):
            # Tag defining all its instances as immutable you can't do a
            # self.name = name
            # so you have to through the parent constructor.
            super().__init__(name=name)

        def group(self):
            # All tags having the same group will be retrieved together by Antidote
            return self.name.split("_")[0]

Antidote will always return a :py:class:`.Tagged`, whether there are tagged instances or
not.

.. note::

    :py:class:`.Tagged` has two generic parameters :code:`T` and :code:`D` which
    respectfully represent the tag type and the dependency type.


Create a stateful factory
-------------------------

Antidote supports stateful factories simply by using defining a class as a factory:

.. testcode:: how_to_stateful_factory

    from antidote import Factory

    class ID:
        def __init__(self, id: str):
            self.id = id

        def __repr__(self):
            return "ID(id='{}')".format(self.id)

    class IDFactory(Factory):
        __antidote__ = Factory.Conf(singleton=False).with_wiring(use_names=True)

        def __init__(self, id_prefix: str):
            self._prefix = id_prefix
            self._next = 1

        def __call__(self) -> ID:
            id = ID("{}_{}".format(self._prefix, self._next))
            self._next += 1
            return id

.. doctest:: how_to_stateful_factory

    >>> from antidote import world
    >>> world.singletons.set('id_prefix', "example")
    >>> world.get[ID](ID @ IDFactory)
    ID(id='example_1')
    >>> world.get[ID](ID @ IDFactory)
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
