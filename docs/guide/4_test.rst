Testing and debugging
=====================


Test with dependencies
----------------------

First and foremost, :py:obj:`.inject` does not hide any arguments, they can always be explicitly given:

.. testcode:: gs_testing

    from antidote import inject, injectable, world


    @injectable
    class Service:
        pass


    @inject
    def f(service: Service = inject.me()) -> Service:
        return service


    assert f() is world[Service]
    test_service = Service()
    assert f(test_service) is test_service

That being said, one can create a test context which isolate dependencies which also allows creating/overriding dependencies easily. Multiple test context can be created, they differ on what to keep from the original catalog (:py:obj:`.world`):

- :py:meth:`~.TestContextBuilder.copy`: Keep all dependency definitions and their values, so the same singleton objects.
- :py:meth:`~.TestContextBuilder.clone`: Keep all dependency definitions.
- :py:meth:`~.TestContextBuilder.new`: The catalog (:py:obj:`.world`) will be untouched, as if just created with :py:func:`.new_catalog`.
- :py:meth:`~.TestContextBuilder.empty`: Totally empty catalog (you'll rarely need this one).

.. testcode:: gs_testing

    original = world[Service]
    with world.test.clone() as overrides:
        # dependency value is different
        assert world[Service] is not original
        # but still a Service and a singleton
        assert isinstance(world[Service], Service)
        assert world[Service] is world[Service]
        assert world[Service] is f()

        # override
        overrides[Service] = 'x'
        assert world[Service] == 'x'

        del overrides[Service]
        assert world.get(Service) is None

        overrides.update({Service: 'y'})
        assert world[Service] == 'y'


        @overrides.factory(Service)
        def build_service() -> object:
            return 'z'


        assert world[Service] == 'z'

        # Test context can be nested
        with world.test.clone() as nested_overrides:
            assert world[Service] == 'z'  # kept the factory build_service which returned 'z' again

            nested_overrides[Service] = 'zz'
            assert world[Service] == 'zz'

        # previous test context is still the same
        assert world[Service] == 'z'

    # Outside the test context, nothing changed.
    assert world[Service] is original


Debug dependencies
------------------

The catalog, :py:obj:`.world` can give you some hindsight on what's actually happening. :py:func:`~.ReadOnlyCatalog.debug` returns the tree of dependencies as seen by Antidote which can help get an understanding of what's happening.

.. testcode:: gs_debug

    from antidote import inject, injectable, world, lazy, const


    class Conf:
        HOST = const.env()


    @injectable(lifetime='transient')
    class Service:
        def __init__(self, host: str = inject[Conf.HOST]) -> None:
            pass


    @lazy
    def f(service: Service = inject.me()):
        pass

    world.debug(f())  # would output something like

.. code-block:: text

    🟉 <lazy> f()
    └── ∅ Service
        └── Service.__init__
            └── 🟉 <const> Conf.HOST

    ∅ = transient
    ↻ = bound
    🟉 = singleton
