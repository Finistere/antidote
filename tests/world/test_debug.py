import textwrap
from typing import Union

from antidote import (Constants, factory, Implementation, implementation, inject,
                      LazyCall,
                      LazyMethodCall,
                      Service, Tag, world)


class DebugTestCase:
    def __init__(self, value, expected: str, recursive: Union[int, bool] = True):
        if expected.startswith('\n'):
            expected = textwrap.dedent(expected[1:])
        self.value = value
        self.expected = expected
        self.recursive = recursive


def assert_valid(*test_cases: DebugTestCase):
    for test_case in test_cases:
        assert world.debug.info(test_case.value,
                                recursive=test_case.recursive) == test_case.expected


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

                * = not singleton
                ─f = function
                ─m = method
                ─l = lazy
                    """
        ))

        world.get(Interface)
        assert_valid(DebugTestCase(
            value=Interface,
            expected=f"""
                Permanent link: {prefix}.Interface -> {prefix}.Dummy defined by {prefix}.f
                └── {prefix}.Dummy

                * = not singleton
                ─f = function
                ─m = method
                ─l = lazy
                    """
        ))

    with world.test.clone():
        undefined_expectations = f"""
            * Dynamic link: {prefix}.Interface -> ??? defined by {prefix}.g

            * = not singleton
            ─f = function
            ─m = method
            ─l = lazy
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

        assert_valid(
            DebugTestCase(
                value=LazyCall(f)("arg", hello="world"),
                expected=f"""
                    Lazy '{prefix}.f' with args=('arg',) and kwargs={{'hello': 'world'}}

                    * = not singleton
                    ─f = function
                    ─m = method
                    ─l = lazy
                    """
            ),
            DebugTestCase(
                value=LazyCall(f, singleton=False)("arg", hello="world"),
                expected=f"""
                    * Lazy '{prefix}.f' with args=('arg',) and kwargs={{'hello': 'world'}}

                    * = not singleton
                    ─f = function
                    ─m = method
                    ─l = lazy
                    """
            ))

    with world.test.new():
        class MyService(Service):
            pass

        @inject
        def f(service: MyService):
            pass

        assert_valid(
            DebugTestCase(
                value=LazyCall(f),
                expected=f"""
                    LazyCall {prefix}.f
                    └─f {prefix}.f
                        └── {prefix}.MyService

                    * = not singleton
                    ─f = function
                    ─m = method
                    ─l = lazy
                    """
            ))


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
                └─/!\\ Unknown: {prefix}.Service1

                * = not singleton
                ─f = function
                ─m = method
                ─l = lazy
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
                └─m get
                    └── {prefix}.Service1

                * = not singleton
                ─f = function
                ─m = method
                ─l = lazy
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

                * = not singleton
                ─f = function
                ─m = method
                ─l = lazy
            """
        ))


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
            KW = LazyMethodCall(fetch, singleton=False)(value='1')

        assert_valid(
            DebugTestCase(
                value=Conf.DATA,
                expected=f"""
                    Lazy Method 'fetch'
                    ├─f {prefix}.Conf.fetch
                    │   └── {prefix}.MyService
                    └── {prefix}.Conf

                    * = not singleton
                    ─f = function
                    ─m = method
                    ─l = lazy
                    """
            ),
            DebugTestCase(
                value=Conf.KW,
                expected=f"""
                    * Lazy Method 'fetch' with args=() and kwargs={{'value': '1'}}
                    ├─f {prefix}.Conf.fetch
                    │   └── {prefix}.MyService
                    └── {prefix}.Conf

                    * = not singleton
                    ─f = function
                    ─m = method
                    ─l = lazy
                    """
            ))


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
                Const calling get with '1' on LazyCall(func={prefix}.Conf, singleton=True)
                └── LazyCall {prefix}.Conf

                * = not singleton
                ─f = function
                ─m = method
                ─l = lazy
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
                    Const calling get with '1' on {prefix}.Conf
                    └── {prefix}.Conf

                    * = not singleton
                    ─f = function
                    ─m = method
                    ─l = lazy
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
                Const calling get with '1' on LazyCall(func={prefix}.Conf, singleton=True)
                ├─f {prefix}.Conf.get
                │   └── {prefix}.MyService
                └── LazyCall {prefix}.Conf

                * = not singleton
                ─f = function
                ─m = method
                ─l = lazy
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
                recursive=False,
                expected=f"""
                    * Tag(group={hex(id(tag))})

                    * = not singleton
                    ─f = function
                    ─m = method
                    ─l = lazy
                        """
            ),
            DebugTestCase(
                value=tag,
                recursive=0,
                expected=f"""
                    * Tag(group={hex(id(tag))})

                    * = not singleton
                    ─f = function
                    ─m = method
                    ─l = lazy
                        """
            ),
            DebugTestCase(
                value=tag,
                recursive=1,
                expected=f"""
                    * Tag(group={hex(id(tag))})
                    ├── {prefix}.Service4
                    └── *{prefix}.Service3

                    * = not singleton
                    ─f = function
                    ─m = method
                    ─l = lazy
                        """
            ),
            DebugTestCase(
                value=tag,
                recursive=2,
                expected=f"""
                    * Tag(group={hex(id(tag))})
                    ├── {prefix}.Service4
                    │   ├── *{prefix}.Service3
                    │   ├── {prefix}.Service2 @ {prefix}.build_s2
                    │   └── {prefix}.Service1
                    └── *{prefix}.Service3
                        ├── Static link: {prefix}.Interface -> {prefix}.Service4
                        ├── {prefix}.Service2 @ {prefix}.build_s2
                        └── {prefix}.Service1

                    * = not singleton
                    ─f = function
                    ─m = method
                    ─l = lazy
                        """
            ),
            DebugTestCase(
                value=tag,
                recursive=3,
                expected=f"""
                    * Tag(group={hex(id(tag))})
                    ├── {prefix}.Service4
                    │   ├── *{prefix}.Service3
                    │   │   ├── Static link: {prefix}.Interface -> {prefix}.Service4
                    │   │   ├── {prefix}.Service2 @ {prefix}.build_s2
                    │   │   └── {prefix}.Service1
                    │   ├── {prefix}.Service2 @ {prefix}.build_s2
                    │   │   └─f {prefix}.build_s2
                    │   │       └── {prefix}.Service1
                    │   └── {prefix}.Service1
                    └── *{prefix}.Service3
                        ├── Static link: {prefix}.Interface -> {prefix}.Service4
                        │   └── {prefix}.Service4
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
            DebugTestCase(
                value=tag,
                expected=f"""
                    * Tag(group={hex(id(tag))})
                    ├── {prefix}.Service4
                    │   ├── *{prefix}.Service3
                    │   │   ├── Static link: {prefix}.Interface -> {prefix}.Service4
                    │   │   │   └─/!\\ Cyclic dependency: {prefix}.Service4
                    │   │   ├── {prefix}.Service2 @ {prefix}.build_s2
                    │   │   │   └─f {prefix}.build_s2
                    │   │   │       └── {prefix}.Service1
                    │   │   └── {prefix}.Service1
                    │   ├── {prefix}.Service2 @ {prefix}.build_s2
                    │   │   └─f {prefix}.build_s2
                    │   │       └── {prefix}.Service1
                    │   └── {prefix}.Service1
                    └── *{prefix}.Service3
                        ├── Static link: {prefix}.Interface -> {prefix}.Service4
                        │   └── {prefix}.Service4
                        │       ├─/!\\ Cyclic dependency: {prefix}.Service3
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
            DebugTestCase(
                value=f,
                expected=f"""
                    {prefix}.f
                    └── {prefix}.Service4
                        ├── *{prefix}.Service3
                        │   ├── Static link: {prefix}.Interface -> {prefix}.Service4
                        │   │   └─/!\\ Cyclic dependency: {prefix}.Service4
                        │   ├── {prefix}.Service2 @ {prefix}.build_s2
                        │   │   └─f {prefix}.build_s2
                        │   │       └── {prefix}.Service1
                        │   └── {prefix}.Service1
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
            DebugTestCase(
                value=f_with_options,
                expected=f"""
                    {prefix}.f_with_options
                    ├── {prefix}.Service2 @ {prefix}.build_s2 with kwargs={{'option': 2}}
                    │   └─f {prefix}.build_s2
                    │       └── {prefix}.Service1
                    └── {prefix}.Service1 with kwargs={{'test': 1}}

                    * = not singleton
                    ─f = function
                    ─m = method
                    ─l = lazy
                    """
            )
        )
