How to
======


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

    >>> from antidote import world
    >>> world.get(IService)
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

    >>> world.update_singletons({Profile: Profile.POSTGRES})
    >>> world.get(Database)
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

    >>> from antidote import world, Tagged
    >>> services = world.get(Tagged('extension'))
    >>> list(zip(services.tags(), services.dependencies(), services.instances()))
    [(Tag(name='extension', version=1), <class 'Service'>, <Service object at ...>), (Tag(name='extension', version=2), <class 'Service2'>, <Service2 object at ...>)]


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

    >>> from antidote import world
    >>> world.get('random')
    0...
    >>> world.get('random') is world.get('random')
    False

Provider are in most cases tried sequentially. So if a provider returns nothing,
it is simply ignored and another provider is tried. For the same reason it is not
recommended to have a lot of different :py:class:`.DependencyProvider`\ s as this
implies a performance penalty.