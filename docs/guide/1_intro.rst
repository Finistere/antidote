Introduction
============


Antidote works with a :py:class:`.Catalog` which is a sort of collection of dependencies. Multiple
ones can co-exist, but :py:obj:`.world` is used by default. The most common form of a dependency is an
instance of a given class

.. doctest:: gs_intro

    >>> from antidote import injectable, world
    >>> @injectable
    ... class Service:
    ...    pass
    >>> world[Service]
    <Service object ...>

By default, :py:func:`.injectable` defines a singleton, at most one instance will be created

.. doctest:: gs_intro

    >>> world[Service] is world[Service]
    True

Dependencies can also be injected into a function/method with :py:obj:`.inject`.

.. doctest:: gs_intro

    >>> from antidote import inject
    >>> @inject
    ... def f(service: Service = inject.me()) -> Service:
    ...     return service
    >>> f()
    <Service object ...>
    >>> f() is world[Service]
    True

Specifying the dependency for each argument can be done in various ways. In the previous example it
relied on the type hint. In all cases it's always explicit, :py:obj:`.inject` won't guess whether
some argument should be injected or not. Here are some of the alternative styles:

.. testcode:: gs_intro

    from antidote import InjectMe

    @inject
    def f2(service = inject[Service]):
        ...

    @inject(kwargs=dict(service=Service))
    def f3(service):
        ...

    @inject
    def f4(service: InjectMe[Service]):
        ...

All of this can be easily tested either by passing explicitly arguments to override the injection or
by overriding globally a dependency with :py:obj:`.world`:

.. doctest:: gs_intro

    >>> original = world[Service]
    >>> x = Service()
    >>> x is original  # different object
    False
    >>> f(x) is x  # overriding injection
    True
    >>> with world.test.clone() as overrides:
    ...     overrides[Service] = x  # overriding Service for the whole catalog
    ...     world[Service] is x, f() is x
    (True, True)
    >>> world[Service] is original  # outside the test context, nothing has changed.
    True
