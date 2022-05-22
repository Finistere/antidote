# pyright: reportUnusedFunction=false
import os
from enum import Enum
from typing import Any, cast, ClassVar, Iterator, Optional, Tuple, Type, TypeVar, Union

import pytest
from typing_extensions import Protocol

from antidote import const, inject, injectable, world
from antidote.core.exceptions import DependencyInstantiationError
from antidote.lib.injectable import register_injectable_provider
from antidote.lib.lazy import Constant, register_lazy_provider

T = TypeVar("T")


class Choice(Enum):
    YES = "YES"
    NO = "NO"


class Unknown:
    pass


@pytest.fixture(autouse=True)
def setup_tests(monkeypatch: Any) -> Iterator[None]:
    monkeypatch.setenv("HOST", "localhost")
    monkeypatch.setenv("PORT", "80")
    monkeypatch.setenv("CHOICE", "YES")
    monkeypatch.delenv("MISSING", raising=False)

    with world.test.empty():
        register_lazy_provider()
        register_injectable_provider()
        yield


def test_static():
    class Conf:
        HOST = const("host")
        PORT = const(80)

    assert world.get[str](Conf.HOST) == "host"
    assert world.get[int](Conf.PORT) == 80

    @inject
    def f(host: str = Conf.HOST, port: int = Conf.PORT) -> Tuple[str, int]:
        return host, port

    assert f() == ("host", 80)

    conf = Conf()
    assert conf.HOST == "host"
    assert conf.PORT == 80


class ConfProtocol(Protocol):
    HOST: ClassVar[Constant[str]]
    HOSTNAME: ClassVar[Constant[str]]
    PORT: ClassVar[Constant[int]]
    PORT_NUMBER: ClassVar[Constant[int]]
    CHOICE: ClassVar[Constant[Choice]]
    UNSUPPORTED_TYPE: ClassVar[Constant[Unknown]]
    MISSING: ClassVar[Constant[str]]
    MISSING_WITH_DEFAULT: ClassVar[Constant[str]]


def check_conf(Conf: Type[ConfProtocol]) -> None:
    assert world.get[str](Conf.HOST) == "localhost"
    assert world.get[str](Conf.HOSTNAME) == "localhost"
    assert world.get[int](Conf.PORT) == 80
    assert world.get[int](Conf.PORT_NUMBER) == 80
    assert world.get[Choice](Conf.CHOICE) == Choice.YES
    assert world.get[str](Conf.MISSING_WITH_DEFAULT) == "default"

    with pytest.raises(DependencyInstantiationError):
        world.get[object](Conf.UNSUPPORTED_TYPE)

    with pytest.raises(TypeError):
        _ = Conf().UNSUPPORTED_TYPE

    with pytest.raises(DependencyInstantiationError):
        world.get[object](Conf.MISSING)

    @inject
    def check(
        host: str = Conf.HOST,
        hostname: str = Conf.HOSTNAME,
        port: int = Conf.PORT,
        port_number: int = Conf.PORT_NUMBER,
        choice: Choice = Conf.CHOICE,
        missing_with_default: str = Conf.MISSING_WITH_DEFAULT,
    ) -> None:
        assert host == "localhost"
        assert hostname == "localhost"
        assert port == 80
        assert port_number == 80
        assert choice == Choice.YES
        assert missing_with_default == "default"

    check()

    conf = Conf()
    assert conf.HOST == "localhost"
    assert conf.HOSTNAME == "localhost"
    assert conf.PORT == 80
    assert conf.PORT_NUMBER == 80
    assert conf.CHOICE == Choice.YES
    assert conf.MISSING_WITH_DEFAULT == "default"


def env_converter(value: str, tpe: Type[T]) -> T:
    if issubclass(tpe, (int, str, float, Enum)):
        return tpe(value)
    raise TypeError()


def test_env():
    class Conf:
        HOST = const.env()
        HOSTNAME = const.env("HOST")
        PORT = const.env[int]()
        PORT_NUMBER = const.env[int]("PORT")
        CHOICE = const.env[Choice]()
        UNSUPPORTED_TYPE = const.env[Unknown]("HOST")
        MISSING = const.env()
        MISSING_WITH_DEFAULT = const.env(default="default")

    check_conf(Conf)


def test_factory_env_external():
    @const.provider
    def env(name: str, arg: Optional[str]) -> str:
        return os.environ[arg or name]

    env.converter(env_converter)

    assert env(name="HOST", arg=None) == "localhost"
    assert env(name="XXX", arg="HOST") == "localhost"

    class Conf:
        HOST = env.const()
        HOSTNAME = env.const("HOST")
        PORT = env.const[int]()
        PORT_NUMBER = env.const[int]("PORT")
        CHOICE = env.const[Choice]()
        UNSUPPORTED_TYPE = env.const[Unknown]("HOST")
        MISSING = env.const()
        MISSING_WITH_DEFAULT = env.const(default="default")

    def _env(name: str, arg: Optional[str]) -> str:
        return os.environ[arg or name]

    env2 = const.provider(_env)
    env2.converter(env_converter)

    class ConfVariable:
        HOST = env2.const()
        HOSTNAME = env2.const("HOST")
        PORT = env2.const[int]()
        PORT_NUMBER = env2.const[int]("PORT")
        CHOICE = env2.const[Choice]()
        UNSUPPORTED_TYPE = env2.const[Unknown]("HOST")
        MISSING = env2.const()
        MISSING_WITH_DEFAULT = env2.const(default="default")

    check_conf(Conf)
    check_conf(ConfVariable)


def test_factory_env_method():
    @injectable
    class Conf:
        @const.provider
        def env(self, name: str, arg: Optional[str]) -> str:
            assert isinstance(self, Conf)
            return os.environ[arg or name]

        env.converter(env_converter)

        HOST = env.const()
        HOSTNAME = env.const("HOST")
        PORT = env.const[int]()
        PORT_NUMBER = env.const[int]("PORT")
        CHOICE = env.const[Choice]()
        UNSUPPORTED_TYPE = env.const[Unknown]("HOST")
        MISSING = env.const()
        MISSING_WITH_DEFAULT = env.const(default="default")

    check_conf(Conf)

    conf = Conf()
    assert conf.env(name="HOST", arg=None) == "localhost"
    assert conf.env(name="XXX", arg="HOST") == "localhost"


def test_invalid_factory():
    with pytest.raises(TypeError, match="provider.*function"):
        const.provider(object())  # type: ignore

    with pytest.raises(TypeError, match="name"):

        @const.provider  # type: ignore
        def f(arg: Optional[object]) -> None:
            ...

    with pytest.raises(TypeError, match="arg"):

        @const.provider  # type: ignore
        def f2(name: str) -> None:
            ...


def test_type_enforcement():
    @const.provider
    def f(name: str, arg: Optional[object]) -> int:
        if arg is None:
            raise LookupError()
        return arg  # type: ignore

    class Conf:
        VALID = f.const(1)
        VALID_DEFAULT = f.const(default=1)
        INVALID = f.const("1")

        TYPED_VALID = f.const[str]("1")
        TYPED_VALID_DEFAULT = f.const[str](default="1")
        TYPED_INVALID = f.const[str](1)

    with pytest.raises(TypeError):
        f.const(default="1")  # type: ignore

    with pytest.raises(TypeError):
        _ = Conf().INVALID

    with pytest.raises(TypeError):
        f.const[str](default=1)  # type: ignore

    with pytest.raises(TypeError):
        _ = Conf().TYPED_INVALID

    assert Conf().VALID == 1
    assert Conf().VALID_DEFAULT == 1
    assert Conf().TYPED_VALID == "1"
    assert Conf().TYPED_VALID_DEFAULT == "1"

    assert world.get[int](Conf.VALID) == 1
    assert world.get[int](Conf.VALID_DEFAULT) == 1
    assert world.get[str](Conf.TYPED_VALID) == "1"
    assert world.get[str](Conf.TYPED_VALID_DEFAULT) == "1"


def test_unchecked_type():
    @const.provider
    def f(name: str, arg: Optional[object]) -> Union[str, int]:
        if arg is None:
            raise LookupError()
        return arg  # type: ignore

    x = object()

    class Conf:
        VALID_UNCHECKED = f.const(x)
        VALID_DEFAULT_UNCHECKED = f.const(default=x)  # type: ignore
        TYPED_VALID_UNCHECKED = f.const[Union[int, float]](x)
        TYPED_VALID_DEFAULT_UNCHECKED = f.const[Union[int, float]](default=x)  # type: ignore

    assert Conf().VALID_UNCHECKED is x
    assert Conf().VALID_DEFAULT_UNCHECKED is x
    assert Conf().TYPED_VALID_UNCHECKED is x
    assert Conf().TYPED_VALID_DEFAULT_UNCHECKED is x

    assert world.get[object](Conf.VALID_UNCHECKED) is x
    assert world.get[object](Conf.VALID_DEFAULT_UNCHECKED) is x
    assert world.get[object](Conf.TYPED_VALID_UNCHECKED) is x
    assert world.get[object](Conf.TYPED_VALID_DEFAULT_UNCHECKED) is x


def test_converter():
    @const.provider
    def f(name: str, arg: Optional[object]) -> Union[str, int]:
        if arg is None:
            raise LookupError()
        return arg  # type: ignore

    @f.converter
    def f_converter(value: Union[str, int], tpe: Type[T]) -> T:
        if issubclass(tpe, str):
            return tpe(value)
        return cast(T, value)

    x = object()

    class Conf:
        VALID_UNCHECKED = f.const(x)
        VALID_DEFAULT_UNCHECKED = f.const(default=x)  # type: ignore
        TYPED_CAST = f.const[str](1)
        TYPED_NO_CAST = f.const[int](1)
        TYPED_INVALID_NO_CAST = f.const[int]("1")
        UNSUPPORTED = f.const[Union[str, int]](1)

    with pytest.raises(TypeError, match="class"):
        _ = Conf().UNSUPPORTED

    assert Conf().VALID_UNCHECKED is x
    assert Conf().VALID_DEFAULT_UNCHECKED is x
    assert Conf().TYPED_CAST == "1"
    assert Conf().TYPED_NO_CAST == 1

    with pytest.raises(TypeError):
        _ = Conf().TYPED_INVALID_NO_CAST

    assert world.get[object](Conf.VALID_UNCHECKED) is x
    assert world.get[object](Conf.VALID_DEFAULT_UNCHECKED) is x
    assert world.get[str](Conf.TYPED_CAST) == "1"
    assert world.get[int](Conf.TYPED_NO_CAST) == 1


def test_invalid_converter():
    @const.provider
    def get(name: str, arg: object) -> object:
        ...

    with pytest.raises(TypeError, match="converter"):
        get.converter(object())  # type: ignore

    with pytest.raises(TypeError, match="value"):

        @get.converter  # type: ignore
        def f(tpe: Type[T]) -> T:
            ...

    with pytest.raises(TypeError, match="tpe"):

        @get.converter  # type: ignore
        def f2(value: object) -> None:
            ...

    @get.converter
    def f3(value: object, tpe: Type[T]) -> T:
        ...

    with pytest.raises(RuntimeError, match="Converter was already defined"):

        @get.converter
        def f4(value: object, tpe: Type[T]) -> T:
            ...


def test_const_repr():
    class Conf:
        TEST = const("random-value")

    assert "random-value" in repr(Conf.__dict__["TEST"])
    # if a failure happens before __set_name__() was called.
    assert "random-value" in repr(const("random-value"))


def test_singleton_dependency():
    class Conf:
        @const.provider
        def env(self, name: str, arg: Optional[object]) -> str:
            return name

        TEST = env.const()

    assert Conf().TEST == "TEST"

    with pytest.raises(DependencyInstantiationError):
        world.get[object](Conf.TEST)

    @injectable(singleton=False)
    class NotASingleton:
        @const.provider
        def env(self, name: str, arg: Optional[object]) -> str:
            return name

        TEST = env.const()

    assert NotASingleton().TEST == "TEST"

    with pytest.raises(DependencyInstantiationError):
        world.get[object](NotASingleton.TEST)
