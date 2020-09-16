Recipes
=======

This is a collection of how to use certain features of Antidote or simply examples of
what can be done.

Use interfaces
--------------

Exposing services through an interface can be done wth :py:func:`~.implements`
(For now, the underlying class needs to be decorated with :py:func:`~.register` .) :

.. testcode:: how_to_interface

    from antidote import register, implements

    class IService:
        pass

    @implements(IService)
    @register
    class Service(IService):
        pass

.. doctest:: how_to_interface

    >>> from antidote import World
    >>> World.get(IService)
    <Service ...>

Multiple implementations can also be declared:

.. testcode:: how_to_interface

    from enum import Flag, auto

    class Profile(Flag):
        POSTGRES = auto()
        MYSQL = auto()

    class Database:
        pass

    @implements(Database, state=Profile.POSTGRES)
    @register
    class PostgresDB(Database):
        pass

    @implements(Database, state=Profile.MYSQL)
    @register
    class MySQLDB(Database):
        pass

.. doctest:: how_to_interface

    >>> World.singletons.set(Profile, Profile.POSTGRES)
    >>> World.get(Database)
    <PostgresDB ...>

The selected implementation will be chosen based on the value of the
:code:`Profile` dependency. While in the example it is defined as a singleton,
it does not have to be.

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

    from urllib.parse import urljoin
    from antidote import register, LazyMethodCall

    @register
    class ExampleCom:
        def get(url):
            return requests.get(urljoin("https://example.com/", url))

        STATUS = LazyMethodCall(get, singleton=False)("/status")

Lazily calling a method through :py:class:`.LazyMethodCall` requires the class
to be known to Antidote, with :py:func:`.register` typically. The class itself
will only be instantiated when necessary.

.. note::

    In fact :py:class:`.LazyConstantsMeta` uses :py:class:`.LazyMethodCall`
    under the hood to define all the constants. So if you're using the same
    function to declare multiple constants you should consider using it
    instead.


Use tags to retrieve multiple dependencies
------------------------------------------

Tags are a way to retrieve a list of services, such as plugins, extensions, etc...

.. testcode:: how_to_tags

    from antidote import register, Tag

    @register(tags=['dummies', Tag('extension', version=1)])
    class Service:
        pass

    @register(tags=['dummies', Tag('extension', version=2)])
    class Service2:
        pass

.. doctest:: how_to_tags

    >>> from antidote import World, Tagged
        >>> services = World.get(Tagged('extension'))
        >>> list(zip(services.tags(), services.dependencies(), services.values()))
        [(Tag(name='extension', version=1), <class 'Service'>, <Service object at ...>), (Tag(name='extension', version=2), <class 'Service2'>, <Service2 object at ...>)]
    >>> services = World.get(Tagged('extension'))
    >>> list(zip(services.tags(), services.dependencies(), services.instances()))
    [(Tag(name='extension', version=1), <class 'Service'>, <Service object at ...>), (Tag(name='extension', version=2), <class 'Service2'>, <Service2 object at ...>)]


Create a stateful factory
-------------------------

Factories created with :py:func:`.factory` can be more complex than a function:

.. testcode:: how_to_stateful_factory

    from antidote import factory

    class ID:
        def __init__(self, id: str):
            self.id = id

        def __repr__(self):
            return "ID(id='{}')".format(self.id)

    @factory(dependencies=dict(prefix='id_prefix'), singleton=False)
    class IDFactory:
        def __init__(self, prefix: str):
            self._prefix = prefix
            self._next = 1

        def __call__(self) -> ID:
            id = ID("{}_{}".format(self._prefix, self._next))
            self._next += 1
            return id

.. doctest:: how_to_stateful_factory

    >>> from antidote import World
    >>> World.singletons.set('id_prefix', "example")
    >>> World.get(ID)
    ID(id='example_1')
    >>> World.get(ID)
    ID(id='example_2')

In this example we choose to inject :code:`id_prefix` in the :code:`__init__()`, but we
also could have done it in the :code:`__call__()`. Both are injected by default, bu they
have different use cases. The factory itself is always a singleton, so static dependencies
should be injected through :code:`__init__()`. If you need dependencies that changes, get
them through :code:`__call__()`. Obviously you can change that behavior through the
:code:`auto_wire` argument.

You might be thinking that one could avoid the use of the class :code:`ID`, but it provides
a nice feature that isn't obvious in this example: it's easy to find its definition. And
more often than not, the factory will be relatively close to it. Had we used a string as a
dependency id, finding the factory would be a lot harder.

Stateful factories can also be used to provide dependencies that have a more complex scope
than Antidote provides (singleton or different each time). Although, if you need to handle
some scope for multiples dependencies it might be worth just extending Antidote through a
:py:class:`.DependencyProvider`.


Extend Antidote through a Provider
----------------------------------

While Antidote provides several ways to handle your dependencies out of the box, it may
not be enough. But don't worry, Antidote got you covered ! It is designed from the ground
up to have an easily extendable core mechanism. Services, resources and tags are all
handled in the same way, through a custom :py:class:`.DependencyProvider` ::

                      +-------------+
       tag=...  +-----> TagProvider +----+
                      +-------------+    |
                                         |
                   +------------------+  |    +----------+    +-----------+
    @implements +--> IndirectProvider +-------> Provider +----> Container +---> @inject
                   +------------------+  |    +----------+    +-----------+
                                         |
                    +-----------------+  |
     @register  +---> ServiceProvider +--+
                    +-----------------+


The container never handles the instantiation of the dependencies itself, it mostly
handles their scope. Let's suppose you want to inject a random number through Antidote,
without passing through a Service. You could do it the following way:


.. testcode:: how_to_provider

    import random
    from typing import Any, Optional

    import antidote
    from antidote.core import DependencyProvider, DependencyInstance

    @antidote.provider
    class RandomProvider(DependencyProvider):
        def provide(self, dependency: Any) -> Optional[DependencyInstance]:
            if dependency == 'random':
                return DependencyInstance(random.random(), singleton=False)

.. doctest:: how_to_provider

    >>> from antidote import World
    >>> World.get('random')
    0...
    >>> World.get('random') is World.get('random')
    False

Provider are in most cases tried sequentially. So if a provider returns nothing,
it is simply ignored and another provider is tried. For the same reason it is not
recommended to have a lot of different :py:class:`.DependencyProvider`\ s as this
implies a performance penalty.