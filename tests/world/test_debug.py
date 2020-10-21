import textwrap

from antidote import factory, implements, inject, LazyMethodCall, Service, Tag, world


def test_debug():
    with world.test.new():
        tag = Tag()

        class Interface:
            pass

        class Service1(Service):
            pass

        class Service2:
            def __init__(self, service1: Service1):
                self.service1 = service1

        @factory
        def build_s2(service1: Service1) -> Service2:
            return Service2(service1)

        class Service3(Service):
            __antidote__ = Service.Conf(singleton=False,
                                        tags=[tag]).with_wiring(
                methods=['__init__', 'get'],
                dependencies=dict(
                    service2=Service2 @ build_s2))

            def __init__(self, service1: Service1, service2: Service2, i: Interface):
                self.service1 = service1
                self.service2 = service2
                self.i = i

            def get(self, service1: Service1):
                pass

            X = LazyMethodCall(get)

        @implements(Interface)
        class Service4(Service, Interface):
            __antidote__ = Service.Conf(tags=[tag]).with_wiring(
                dependencies=dict(service2=Service2 @ build_s2))

            def __init__(self, service1: Service1, service2: Service2,
                         service3: Service3):
                self.service1 = service1
                self.service2 = service2
                self.service3 = service3

        @inject
        def f(s: Service4):
            pass

        def g():
            pass

        def test_case(value, expected):
            if expected.startswith('\n'):
                expected = textwrap.dedent(expected[1:])
            return value, expected

        prefix = "tests.world.test_debug.test_debug.<locals>"
        for value, expected in [
            test_case(
                value=tag,
                expected=f"""
                        Tag(group={hex(id(tag))})
                        ├── {prefix}.Service4
                        │   ├── *{prefix}.Service3
                        │   │   ├─l X <Lazy Method 'get'>
                        │   │   │   └── {prefix}.Service1
                        │   │   ├─m get
                        │   │   │   └── {prefix}.Service1
                        │   │   └─m __init__
                        │   │       ├── Static link: {prefix}.Interface -> {prefix}.Service4
                        │   │       │   └─/!\\ Cyclic dependency on {prefix}.Service4
                        │   │       ├── {prefix}.Service2 @ {prefix}.build_s2
                        │   │       │   └─f {prefix}.build_s2
                        │   │       │       └── {prefix}.Service1
                        │   │       └── {prefix}.Service1
                        │   ├── {prefix}.Service2 @ {prefix}.build_s2
                        │   │   └─f {prefix}.build_s2
                        │   │       └── {prefix}.Service1
                        │   └── {prefix}.Service1
                        └── *{prefix}.Service3
                            ├─l X <Lazy Method 'get'>
                            │   └── {prefix}.Service1
                            ├─m get
                            │   └── {prefix}.Service1
                            └─m __init__
                                ├── Static link: {prefix}.Interface -> {prefix}.Service4
                                │   └── {prefix}.Service4
                                │       ├─/!\\ Cyclic dependency on {prefix}.Service3
                                │       ├── {prefix}.Service2 @ {prefix}.build_s2
                                │       │   └─f {prefix}.build_s2
                                │       │       └── {prefix}.Service1
                                │       └── {prefix}.Service1
                                ├── {prefix}.Service2 @ {prefix}.build_s2
                                │   └─f {prefix}.build_s2
                                │       └── {prefix}.Service1
                                └── {prefix}.Service1
                
                        * = not singleton
                        ─f = function
                        ─m = method
                        ─l = lazy
                        """
            ),
            test_case(
                value=f,
                expected=f"""
                        {prefix}.f
                        └── {prefix}.Service4
                            ├── *{prefix}.Service3
                            │   ├─l X <Lazy Method 'get'>
                            │   │   └── {prefix}.Service1
                            │   ├─m get
                            │   │   └── {prefix}.Service1
                            │   └─m __init__
                            │       ├── Static link: {prefix}.Interface -> {prefix}.Service4
                            │       │   └─/!\\ Cyclic dependency on {prefix}.Service4
                            │       ├── {prefix}.Service2 @ {prefix}.build_s2
                            │       │   └─f {prefix}.build_s2
                            │       │       └── {prefix}.Service1
                            │       └── {prefix}.Service1
                            ├── {prefix}.Service2 @ {prefix}.build_s2
                            │   └─f {prefix}.build_s2
                            │       └── {prefix}.Service1
                            └── {prefix}.Service1
                
                        * = not singleton
                        ─f = function
                        ─m = method
                        ─l = lazy
                        """
            ),
            test_case(
                value=g,
                expected=f"""{g!r} is neither a dependency nor is anything injected."""
            )
        ]:  # noqa
            assert world.debug.info(value, recursive=True) == expected
