from typing import cast, Optional, overload

from typing_extensions import Annotated, Protocol

from antidote import (const, Constants, factory, From, Get, inject, Provide, Service, world)


def test_constants_typing() -> None:
    with world.test.new():
        class MyService(Service):
            pass

        world.test.singleton('test', [])
        world.get[list]('test').append(1)
        world.lazy[list]('test').get().append(2)

        class Conf(Constants):
            A = const[list]("a")
            B = const[list]("b", default=[2])

            @inject
            def provide_const(self,
                              name: str,
                              arg: object,
                              my_service: Optional[Provide[MyService]] = None
                              ) -> object:
                assert isinstance(my_service, MyService)
                return []

        Conf().A.append(1)


def test_annotated_typing() -> None:
    with world.test.new():
        class Dummy:
            def hello(self) -> 'Dummy':
                return self

        world.test.singleton('dummy', Dummy())

        @factory
        def build_dummy() -> Dummy:
            return Dummy()

        @inject
        def f(dummy: Optional[Annotated[Dummy, Get('dummy')]] = None) -> Dummy:  # noqa: F821, E501
            assert dummy is not None
            return dummy

        assert f().hello() is world.get[Dummy](
            Annotated[Dummy, Get('dummy')])  # noqa: F821, E501
        assert world.get[Dummy](Annotated[Dummy, Get('dummy')]) \
               is world.get[Dummy]('dummy')

        @inject
        def g(dummy: Optional[Annotated[Dummy, From(build_dummy)]] = None) -> Dummy:
            assert dummy is not None
            return dummy

        assert g().hello() is world.get[Dummy](Dummy @ build_dummy)


def test_proper_typing_assert_none() -> None:
    with world.test.new():
        class MyService(Service):
            pass

        @inject
        def f(my_service: Optional[Provide[MyService]] = None) -> MyService:
            # We never expect it to be None, but it Mypy will now
            # understand that my_service may not be provided.
            assert my_service is not None
            return my_service

        s: MyService = f()  # noqa: F841

        # You can also overload the function, if you want a more accurate type definition:
        from typing import overload

        @overload
        def g(my_service: MyService) -> MyService: ...  # noqa: E704

        @overload
        def g() -> MyService: ...  # noqa: E704

        @inject
        def g(my_service: Optional[Provide[MyService]] = None) -> MyService:
            assert my_service is not None
            return my_service

        s2: MyService = g()  # noqa: F841


def test_proper_typing_protocol() -> None:
    with world.test.new():
        class MyService(Service):
            pass

        @inject
        def f(my_service: Provide[MyService]) -> MyService:
            return my_service

        class FProtocol(Protocol):
            @overload
            def __call__(self, my_service: Service) -> MyService: ...  # noqa: E704

            @overload
            def __call__(self) -> MyService: ...  # noqa: E704

            def __call__(self, my_service: Optional[Service] = None) -> MyService: ...  # noqa: E704

        ff = cast(FProtocol, f)

        s: MyService = ff()  # noqa: F841
