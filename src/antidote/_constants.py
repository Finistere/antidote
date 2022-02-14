from __future__ import annotations

from typing import (Any, cast, Dict, Generic, Hashable, Optional, Tuple, Type,
                    TYPE_CHECKING, TypeVar, Union)

from typing_extensions import final

from ._internal import API
from ._internal.utils import AbstractMeta, debug_repr, Default, enforce_type_if_possible, \
    FinalImmutable, FinalMeta
from ._internal.utils.immutable import Immutable
from ._providers.lazy import Lazy
from .core import Container, DependencyDebug, DependencyValue, Scope
from .core.marker import Marker
from .core.typing import Dependency

if TYPE_CHECKING:
    from .constants import Constants

T = TypeVar('T')
Tco = TypeVar('Tco', covariant=True)


@API.private
@final
class MakeConst(metaclass=FinalMeta):
    def __call__(self,
                 __arg: Optional[object] = None,
                 *,
                 default: object = Default.sentinel) -> LazyConstDescriptor[object]:
        # Not true yet, but will be changed by ConstantsMeta / @constants
        return cast(LazyConstDescriptor[object], LazyConstToDo(__arg, None, default))

    def __getitem__(self, tpe: Type[T]) -> MakeTypedConst[T]:
        return MakeTypedConst(tpe)


@API.private
@final
class MakeTypedConst(Immutable, Generic[T]):
    __slots__ = ('__type',)
    __type: Type[T]

    def __call__(self,
                 __arg: Optional[object] = None,
                 *,
                 default: Union[T, Default] = Default.sentinel) -> LazyConstDescriptor[T]:
        if default is not Default.sentinel:
            enforce_type_if_possible(default, self.__type)
        # Not true yet, but will be changed by ConstantsMeta / @constants
        return cast(LazyConstDescriptor[T], LazyConstToDo(__arg, self.__type, default))


@API.private
@final
class LazyConstToDo(FinalImmutable):
    __slots__ = ('arg', 'type_', 'default')
    arg: Optional[object]
    type_: Optional[type]
    default: object

    def __get__(self, instance: object, owner: object) -> None:
        raise RuntimeError("const() can only be used in a subclass of Constants.")


@API.private
class ConstantsMeta(AbstractMeta):
    def __new__(mcs: Type[ConstantsMeta],
                name: str,
                bases: Tuple[type, ...],
                namespace: Dict[str, object],
                **kwargs: object
                ) -> ConstantsMeta:
        cls = cast(
            ConstantsMeta,
            super().__new__(mcs, name, bases, namespace, **kwargs)  # type: ignore
        )
        if not kwargs.get('abstract'):
            _configure_constants(cls)
        return cls


@API.private
def _configure_constants(cls: type, conf: object = None) -> None:
    from .constants import Constants
    from .service import service

    conf = conf or getattr(cls, '__antidote__', None)
    if not isinstance(conf, Constants.Conf):
        raise TypeError(f"Constants configuration (__antidote__) is expected to be a "
                        f"{Constants.Conf}, not a {type(conf)}")

    cls = service(cls, singleton=True, wiring=conf.wiring)
    for name, v in list(cls.__dict__.items()):
        if not isinstance(v, LazyConstToDo):
            continue

        descriptor: LazyConstDescriptor[Any] = LazyConstDescriptor(
            name=name,
            dependency=cls,
            method_name=Constants.provide_const.__name__,
            arg=v.arg,
            default=v.default,
            type_=v.type_ or object,
            auto_cast=v.type_ is not None and v.type_ in conf.auto_cast
        )
        setattr(cls, name, descriptor)


@API.private
@final
class LazyConstDescriptor(Generic[Tco], FinalImmutable):
    __slots__ = ('name', 'dependency', 'method_name', 'arg', 'default', 'type_',
                 'auto_cast', '_cache')
    name: str
    dependency: Hashable
    method_name: str
    arg: object
    default: Tco
    type_: type
    auto_cast: bool
    _cache: str

    def __init__(self,
                 *,
                 name: str,
                 dependency: Hashable,
                 method_name: str,
                 arg: object,
                 default: Tco,
                 type_: type,
                 auto_cast: bool
                 ):
        super().__init__(
            name=name,
            dependency=dependency,
            method_name=method_name,
            arg=arg,
            default=default,
            type_=type_,
            auto_cast=auto_cast,
            _cache=f"__antidote_dependency_{hex(id(self))}"
        )

    def __get__(self,
                instance: Optional[Constants],
                owner: Type[Constants]
                ) -> Tco:  # Not true for class instance, but helps with typing errors.
        if instance is None:
            try:
                return cast(Tco, getattr(owner, self._cache))
            except AttributeError:
                dependency = LazyConst(self)
                setattr(owner, self._cache, dependency)

                # Lying to Mypy, but it should help to detect errors when used as a Marker.
                return cast(Tco, dependency)
        try:
            value = getattr(instance, self.method_name)(name=self.name,
                                                        arg=self.arg)
        except LookupError:
            if self.default is not Default.sentinel:
                return self.default
            raise

        if self.auto_cast:
            value = self.type_(value)

        enforce_type_if_possible(value, self.type_)
        return cast(Tco, value)


@API.private
@final
class LazyConst(FinalImmutable, Lazy, Dependency[T], Marker):
    __slots__ = ('descriptor',)
    descriptor: object

    def __init__(self, descriptor: LazyConstDescriptor[T]) -> None:
        super().__init__(descriptor=descriptor)

    def __antidote_debug_info__(self) -> DependencyDebug:
        descriptor = cast(LazyConstDescriptor[T], self.descriptor)
        cls = cast(type, descriptor.dependency)
        return DependencyDebug(f"{debug_repr(cls)}.{descriptor.name}",
                               scope=Scope.singleton(),
                               # TODO: Would be great if the first argument of the method
                               #       didn't show as unknown as it's always provided.
                               wired=[getattr(cls, descriptor.method_name), cls])

    def __antidote_provide__(self, container: Container) -> DependencyValue:
        # TODO: Waiting for a fix: https://github.com/python/mypy/issues/6910
        descriptor = cast(LazyConstDescriptor[T], self.descriptor)
        return DependencyValue(
            getattr(container.get(descriptor.dependency), descriptor.name),
            scope=Scope.singleton()
        )
