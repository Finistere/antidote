from typing import cast, Optional, overload

from typing_extensions import Annotated, Protocol

from antidote import const, Constants, factory, From, Get, inject, Provide, Service, world


def test_constants_typing() -> None:
    with world.test.new():

        class MyService(Service):
            pass

        world.test.singleton("test", [])
        world.get[list]("test").append(1)
        world.lazy[list]("test").get().append(2)

        class Conf(Constants):
            A = const[list]("a")
            B = const[list]("b", default=[2])

            @inject
            def provide_const(
                self, name: str, arg: object, my_service: Optional[Provide[MyService]] = None
            ) -> object:
                assert isinstance(my_service, MyService)
                return []

        Conf().A.append(1)


def test_annotated_typing() -> None:
    with world.test.new():

        class Dummy:
            def hello(self) -> "Dummy":
                return self

        world.test.singleton("dummy", Dummy())

        @factory
        def build_dummy() -> Dummy:
            return Dummy()

        @inject
        def f(dummy: Optional[Annotated[Dummy, Get("dummy")]] = None) -> Dummy:
            assert dummy is not None
            return dummy

        assert f().hello() is world.get[Dummy](Annotated[Dummy, Get("dummy")])
        assert world.get[Dummy](Annotated[Dummy, Get("dummy")]) is world.get[Dummy]("dummy")

        @inject
        def g(dummy: Optional[Annotated[Dummy, From(build_dummy)]] = None) -> Dummy:
            assert dummy is not None
            return dummy

        assert g().hello() is world.get[Dummy](Dummy @ build_dummy)  # type: ignore


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

        _ = f()

        # You can also overload the function, if you want a more accurate type definition:
        from typing import overload

        @overload
        def g(my_service: MyService) -> MyService:
            ...

        @overload
        def g() -> MyService:
            ...

        @inject
        def g(my_service: Optional[Provide[MyService]] = None) -> MyService:
            assert my_service is not None
            return my_service

        _ = g()


def test_proper_typing_protocol() -> None:
    with world.test.new():

        class MyService(Service):
            pass

        @inject
        def f(my_service: Provide[MyService]) -> MyService:
            return my_service

        class FProtocol(Protocol):
            @overload
            def __call__(self, my_service: Service) -> MyService:
                ...

            @overload
            def __call__(self) -> MyService:
                ...

            def __call__(self, my_service: Optional[Service] = None) -> MyService:
                ...

        ff = cast(FProtocol, f)

        _ = ff()
