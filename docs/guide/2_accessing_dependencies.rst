Accessing Dependencies
======================


Dependencies can be either accessed trough a catalog or :py:obj:`.inject`. Both ways provide proper
type hints to allow mypy, pyright and PyCharm to properly detect the type of the dependency values


Catalog
-------

:py:obj:`.world` is an instance of :py:class:`.ReadOnlyCatalog` from which dependencies can be
retrieved with a properly typed dict-like API:

.. testcode:: gs_2_catalog

    from antidote import injectable, inject

    @injectable
    class Service:
        pass

.. doctest:: gs_2_catalog

    >>> Service in world
    True
    >>> world[Service]
    <Service object ...>
    >>> world.get(Service)
    <Service object ...>

And for an unknown dependency:

.. doctest:: gs_2_catalog

    >>> unknown = object()
    >>> unknown in world
    False
    >>> try:
    ...     world[unknown]
    ... except KeyError:
    ...     pass
    >>> world[unknown]
    Traceback (most recent call last):
      File "<stdin>", line 1, in ?
    DependencyNotFoundError: ...
    >>> world.get(unknown) is None
    True
    >>> world.get(unknown, default='x')
    'x'


Injection
---------

:py:obj:`.inject` exposes a very similar API to :py:obj:`.world`, except it won't retrieve the
dependency immediately, it's only done at function call. Any (async-)function and (static/class-)methods
can be injected. The wrapped function will then behave like a transparent proxy, as much as possible.

Binding dependencies to arguments
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
:py:obj:`.inject` supports a variety of ways to bind dependencies to arguments, in order:

.. testcode:: gs_2_inject

    from antidote import injectable, inject

    @injectable
    class Service:
        pass

1. :code:`args` and :code:`kwargs`

    .. testcode:: gs_2_inject

        @inject(args=[Service])
        def f1(service) -> Service:
            return service

        @inject(kwargs=dict(service=Service))
        def f2(service) -> Service:
            return service

2. Default arguments and PEP-593 :py:class:`~typing.Annotated` type hints. :py:meth:`.Inject.me` provides
   a convenient way to use the argument type hint, but it can be explicitly specified:

    .. testcode:: gs_2_inject

        from antidote import InjectMe

        @inject
        def f3(service = inject[Service]) -> Service:
            return service

        @inject  #              ⯆ will inject None if Service is not a dependency
        def f4(service = inject.get(Service)) -> Service:
            return service

        @inject
        def f5(service: Service = inject.me()) -> Service:
            return service

        @inject
        def f6(service: InjectMe[Service]) -> Service:
            return service

3. :code:`fallback` behaves like :code:`kwargs` except it is last to be consulted

    .. testcode:: gs_2_inject

        @inject(fallback=dict(service=Service))
        def f7(service) -> Service:
            return service

.. testcode:: gs_2_inject
    :hide:

    service = world[Service]
    assert f1() is service
    assert f2() is service
    assert f3() is service
    assert f4() is service
    assert f5() is service
    assert f6() is service
    assert f7() is service

.. note::

    It is recommended to use the default values as it helps static type checker such as pyright and
    Mypy to see the "real" signature of the function.

Binding 'self' for methods
^^^^^^^^^^^^^^^^^^^^^^^^^^
While :py:obj:`.inject` can be applied on methods, it's not convenient to inject :code:`self` for
methods of an :py:func:`.injectable` class. So that's exactly the purpose of :py:meth:`.Inject.method`:

.. testcode:: gs_2_inject_method

    from antidote import injectable, inject, world

    @injectable
    class Dummy:
        @inject.method
        def method(self) -> 'Dummy':
            return self

.. doctest:: gs_2_inject_method

    >>> Dummy.method()
    <Dummy object ...>
    >>> Dummy.method() is world[Dummy]
    True

As shown the wrapped method now behaves like a class method and be called directly on the class. But it
can also be called on a instance, in which case the injection will be overridden:

.. doctest:: gs_2_inject_method

    >>> dummy = Dummy()
    >>> dummy.method() is dummy
    True

Injecting multiple methods / wiring a class
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
To apply :py:obj:`.inject` on all methods, or a subset, :py:func:`.wire` can be used. It won't
change any existing injection, so custom injection for a method can be easily applied:

.. testcode:: gs_2_inject_wire

    from antidote import wire, injectable, inject

    @injectable
    class Service:
        pass

    @wire
    class Dummy:
        def method(self, service: Service = inject.me()) -> Service:
            return service
        @inject(kwargs=dict(service=Service))
        def custom(self, service) -> Service:
            return service

.. doctest:: gs_2_inject_wire

    >>> dummy = Dummy()
    >>> dummy.method()
    <Service object ...>
    >>> dummy.custom()
    <Service object ...>

.. note::

    Underneath :py:func:`.wire` relies on :py:class:`.Wiring`.
