import textwrap

from antidote import (Constants, factory, Implementation, implementation, inject,
                      LazyCall, LazyMethodCall, Service, Tag, world)
from antidote._internal.utils import raw_getattr, short_id


class DebugTestCase:
    def __init__(self, value, expected: str, depth: int = -1):
        if expected.startswith('\n'):
            expected = textwrap.dedent(expected[1:])
        lines = expected.splitlines(keepends=True)
        while not lines[-1].strip():
            lines.pop()

        self.value = value
        self.expected = ''.join(lines)
        self.depth = depth


def assert_valid(*test_cases: DebugTestCase):
    for test_case in test_cases:
        assert world.debug(test_case.value,
                           depth=test_case.depth) == test_case.expected


def test_no_debug():
    def g():
        pass

    assert_valid(
        DebugTestCase(
            value=g,
            expected=f"""{g!r} is neither a dependency nor is anything injected."""
        )
    )


def test_implementation_debug():
    class Interface:
        pass

    class Dummy(Interface, Service):
        pass

    prefix = "tests.world.test_debug.test_implementation_debug.<locals>"

    with world.test.clone():
        @implementation(Interface)
        def f():
            return Dummy

        assert_valid(DebugTestCase(
            value=Interface,
            expected=f"""
                Permanent link: {prefix}.Interface -> ??? defined by {prefix}.f
                    """
        ))

        world.get(Interface)
        assert_valid(DebugTestCase(
            value=Interface,
            expected=f"""
                Permanent link: {prefix}.Interface -> {prefix}.Dummy defined by {prefix}.f
                └── {prefix}.Dummy
                    """
        ))

    with world.test.clone():
        undefined_expectations = f"""
            * Dynamic link: {prefix}.Interface -> ??? defined by {prefix}.g

            * = not singleton
        """

        @implementation(Interface, permanent=False)
        def g():
            return Dummy

        assert_valid(DebugTestCase(value=Interface,
                                   expected=undefined_expectations))

        world.get(Interface)
        assert_valid(DebugTestCase(value=Interface,
                                   expected=undefined_expectations))


def test_lazy_call_debug():
    prefix = "tests.world.test_debug.test_lazy_call_debug.<locals>"

    with world.test.new():
        def f():
            pass

        l1 = LazyCall(f)("arg", hello="world")
        assert_valid(
            DebugTestCase(
                value=l1,
                expected=f"""
                    Lazy: {prefix}.f(*('arg',), **{{'hello': 'world'}})  #{short_id(l1)}
                    """
            ),
            DebugTestCase(
                value=LazyCall(f, singleton=False)("arg", hello="world"),
                expected=f"""
                    * Lazy: {prefix}.f(*('arg',), **{{'hello': 'world'}})

                    * = not singleton
                    """
            ))

    with world.test.new():
        class MyService(Service):
            pass

        @inject
        def f(service: MyService):
            pass

        l2 = LazyCall(f)
        assert_valid(
            DebugTestCase(
                value=l2,
                expected=f"""
                    Lazy: {prefix}.f()  #{short_id(l2)}
                    └── {prefix}.f
                        └── {prefix}.MyService
                    """
            ),
            DebugTestCase(
                value=LazyCall(f, singleton=False),
                expected=f"""
                    * Lazy: {prefix}.f()
                    └── {prefix}.f
                        └── {prefix}.MyService

                    * = not singleton
                    """
            )
        )


def test_unknown_debug():
    prefix = "tests.world.test_debug.test_unknown_debug.<locals>"

    with world.test.new():
        class Service1:
            pass

        class Dummy(Service):
            def __init__(self, s: Service1):
                pass

        assert_valid(DebugTestCase(
            value=Dummy,
            expected=f"""
                {prefix}.Dummy
                └── /!\\ Unknown: {prefix}.Service1
            """
        ))


def test_singleton_debug():
    with world.test.new():
        world.singletons.add("test", 1)

        assert_valid(DebugTestCase(
            value="test",
            expected="""
                Singleton 'test' -> 1
            """
        ))


def test_wiring_debug():
    prefix = "tests.world.test_debug.test_wiring_debug.<locals>"

    with world.test.new():
        class Service1(Service):
            pass

        class Dummy(Service):
            __antidote__ = Service.Conf().with_wiring(methods=['__init__', 'get'])

            def __init__(self, s: Service1):
                pass

            def get(self, s: Service1):
                pass

        assert_valid(DebugTestCase(
            value=Dummy,
            expected=f"""
                {prefix}.Dummy
                ├── {prefix}.Service1
                └── Method: get
                    └── {prefix}.Service1
            """
        ))


def test_multiline_debug():
    prefix = "tests.world.test_debug.test_multiline_debug.<locals>"

    with world.test.new():
        class MultilineService(Service):
            @classmethod
            def __antidote_debug_repr__(cls):
                return "Multiline\nService"

        class Dummy(Service):
            def __init__(self, s: MultilineService):
                pass

        assert_valid(DebugTestCase(
            value=Dummy,
            expected=f"""
                {prefix}.Dummy
                └── Multiline
                    Service
            """
        ))


def test_tag():
    prefix = "tests.world.test_debug.test_tag.<locals>"

    with world.test.new():
        tag = Tag()

        class CustomTag(Tag):
            def group(self):
                return 'dummy'

        class S1(Service):
            __antidote__ = Service.Conf(tags=[tag, CustomTag()])

        assert_valid(
            DebugTestCase(
                value=tag,
                expected=f"""
                * Tag: Tag#{short_id(tag)}
                └── {prefix}.S1

                * = not singleton
                """
            ),
            DebugTestCase(
                value=CustomTag(),
                expected=f"""
                * Tag: 'dummy'
                └── {prefix}.S1

                * = not singleton
                """
            )
        )


def test_lazy_method_debug():
    prefix = "tests.world.test_debug.test_lazy_method_debug.<locals>"

    with world.test.new():
        class MyService(Service):
            pass

        class Conf(Service):
            @inject
            def fetch(self, value, service: MyService):
                return value

            DATA = LazyMethodCall(fetch)
            KW = LazyMethodCall(fetch)(value='1')
            DATA2 = LazyMethodCall(fetch, singleton=False)
            KW2 = LazyMethodCall(fetch, singleton=False)(value='2')

        assert_valid(
            DebugTestCase(
                value=Conf.DATA,
                expected=f"""
                    Lazy Method: fetch()  #{short_id(raw_getattr(Conf, 'DATA'))}
                    ├── {prefix}.Conf.fetch
                    │   └── {prefix}.MyService
                    └── {prefix}.Conf
                    """
            ),
            DebugTestCase(
                value=Conf.KW,
                expected=f"""
        Lazy Method: fetch(*(), **{{'value': '1'}})  #{short_id(raw_getattr(Conf, 'KW'))}
        ├── {prefix}.Conf.fetch
        │   └── {prefix}.MyService
        └── {prefix}.Conf
                    """
            ),
            DebugTestCase(
                value=Conf.DATA2,
                expected=f"""
                    * Lazy Method: fetch()
                    ├── {prefix}.Conf.fetch
                    │   └── {prefix}.MyService
                    └── {prefix}.Conf

                    * = not singleton
                    """
            ),
            DebugTestCase(
                value=Conf.KW2,
                expected=f"""
                    * Lazy Method: fetch(*(), **{{'value': '2'}})
                    ├── {prefix}.Conf.fetch
                    │   └── {prefix}.MyService
                    └── {prefix}.Conf

                    * = not singleton
                    """
            )
        )


def test_constants_debug():
    prefix = "tests.world.test_debug.test_constants_debug.<locals>"

    with world.test.new():
        class Conf(Constants):
            TEST = '1'

            def get(self, value):
                return value

        assert_valid(
            DebugTestCase(
                value=Conf.TEST,
                expected=f"""
            Const: {prefix}.Conf.TEST
            └── Lazy: {prefix}.Conf()  #{short_id(raw_getattr(Conf, 'TEST').dependency)}
                    """
            ))

    with world.test.new():
        class Conf(Constants):
            __antidote__ = Constants.Conf(public=True)

            TEST = '1'

            def get(self, value):
                return value

        assert_valid(
            DebugTestCase(
                value=Conf.TEST,
                expected=f"""
                    Const: {prefix}.Conf.TEST
                    └── {prefix}.Conf
                    """
            ))

    with world.test.new():
        class MyService(Service):
            pass

        class Conf(Constants):
            TEST = '1'

            @inject
            def get(self, value, service: MyService):
                return value

        assert_valid(
            DebugTestCase(
                value=Conf.TEST,
                expected=f"""
            Const: {prefix}.Conf.TEST
            ├── {prefix}.Conf.get
            │   └── {prefix}.MyService
            └── Lazy: {prefix}.Conf()  #{short_id(raw_getattr(Conf, 'TEST').dependency)}
                    """
            ))


def test_complex_debug():
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

        class Service4(Interface, Implementation):
            __antidote__ = Implementation.Conf(tags=[tag]).with_wiring(
                dependencies=dict(service2=Service2 @ build_s2))

            def __init__(self, service1: Service1, service2: Service2,
                         service3: Service3):
                self.service1 = service1
                self.service2 = service2
                self.service3 = service3

        @inject
        def f(s: Service4):
            pass

        @inject(dependencies=[Service1.with_kwargs(test=1),
                              Service2 @ build_s2.with_kwargs(option=2)])
        def f_with_options(a, b):
            pass

        prefix = "tests.world.test_debug.test_complex_debug.<locals>"
        assert_valid(
            DebugTestCase(
                value=tag,
                depth=0,
                expected=f"""
                    * Tag: Tag#{short_id(tag)}

                    * = not singleton
                        """
            ),
            DebugTestCase(
                value=tag,
                depth=1,
                expected=f"""
                    * Tag: Tag#{short_id(tag)}
                    ├── {prefix}.Service4
                    └── * {prefix}.Service3

                    * = not singleton
                        """
            ),
            DebugTestCase(
                value=tag,
                depth=2,
                expected=f"""
                    * Tag: Tag#{short_id(tag)}
                    ├── {prefix}.Service4
                    │   ├── * {prefix}.Service3
                    │   ├── {prefix}.Service2 @ {prefix}.build_s2
                    │   └── {prefix}.Service1
                    └── * {prefix}.Service3
                        ├── Static link: {prefix}.Interface -> {prefix}.Service4
                        ├── {prefix}.Service2 @ {prefix}.build_s2
                        └── {prefix}.Service1

                    * = not singleton
                        """
            ),
            DebugTestCase(
                value=tag,
                depth=3,
                expected=f"""
                    * Tag: Tag#{short_id(tag)}
                    ├── {prefix}.Service4
                    │   ├── * {prefix}.Service3
                    │   │   ├── Static link: {prefix}.Interface -> {prefix}.Service4
                    │   │   ├── {prefix}.Service2 @ {prefix}.build_s2
                    │   │   └── {prefix}.Service1
                    │   ├── {prefix}.Service2 @ {prefix}.build_s2
                    │   │   └── {prefix}.build_s2
                    │   │       └── {prefix}.Service1
                    │   └── {prefix}.Service1
                    └── * {prefix}.Service3
                        ├── Static link: {prefix}.Interface -> {prefix}.Service4
                        │   └── {prefix}.Service4
                        ├── {prefix}.Service2 @ {prefix}.build_s2
                        │   └── {prefix}.build_s2
                        │       └── {prefix}.Service1
                        └── {prefix}.Service1

                    * = not singleton
                        """
            ),
            DebugTestCase(
                value=tag,
                expected=f"""
                    * Tag: Tag#{short_id(tag)}
                    ├── {prefix}.Service4
                    │   ├── * {prefix}.Service3
                    │   │   ├── Static link: {prefix}.Interface -> {prefix}.Service4
                    │   │   │   └── /!\\ Cyclic dependency: {prefix}.Service4
                    │   │   ├── {prefix}.Service2 @ {prefix}.build_s2
                    │   │   │   └── {prefix}.build_s2
                    │   │   │       └── {prefix}.Service1
                    │   │   └── {prefix}.Service1
                    │   ├── {prefix}.Service2 @ {prefix}.build_s2
                    │   │   └── {prefix}.build_s2
                    │   │       └── {prefix}.Service1
                    │   └── {prefix}.Service1
                    └── * {prefix}.Service3
                        ├── Static link: {prefix}.Interface -> {prefix}.Service4
                        │   └── {prefix}.Service4
                        │       ├── /!\\ Cyclic dependency: {prefix}.Service3
                        │       ├── {prefix}.Service2 @ {prefix}.build_s2
                        │       │   └── {prefix}.build_s2
                        │       │       └── {prefix}.Service1
                        │       └── {prefix}.Service1
                        ├── {prefix}.Service2 @ {prefix}.build_s2
                        │   └── {prefix}.build_s2
                        │       └── {prefix}.Service1
                        └── {prefix}.Service1

                    * = not singleton
                        """
            ),
            DebugTestCase(
                value=f,
                expected=f"""
                    {prefix}.f
                    └── {prefix}.Service4
                        ├── * {prefix}.Service3
                        │   ├── Static link: {prefix}.Interface -> {prefix}.Service4
                        │   │   └── /!\\ Cyclic dependency: {prefix}.Service4
                        │   ├── {prefix}.Service2 @ {prefix}.build_s2
                        │   │   └── {prefix}.build_s2
                        │   │       └── {prefix}.Service1
                        │   └── {prefix}.Service1
                        ├── {prefix}.Service2 @ {prefix}.build_s2
                        │   └── {prefix}.build_s2
                        │       └── {prefix}.Service1
                        └── {prefix}.Service1

                    * = not singleton
                        """
            ),
            DebugTestCase(
                value=f_with_options,
                expected=f"""
                    {prefix}.f_with_options
                    ├── {prefix}.Service2 @ {prefix}.build_s2(**{{'option': 2}})
                    │   └── {prefix}.build_s2
                    │       └── {prefix}.Service1
                    └── {prefix}.Service1(**{{'test': 1}})
                    """
            )
        )
