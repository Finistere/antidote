from typing import (Any, Dict, Generic, Hashable, Optional, TYPE_CHECKING, Tuple, Type,
                    TypeVar, Union, cast, overload)

from ._compatibility.typing import final, Protocol
from ._internal import API
from ._internal.utils import AbstractMeta, Default, FinalImmutable, FinalMeta, debug_repr
from ._internal.utils.immutable import Immutable, ImmutableGenericMeta
from ._providers.lazy import Lazy
from .core import Container, DependencyDebug, DependencyValue, Scope

T = TypeVar('T')

if TYPE_CHECKING:
    from .constants import Constants


# TODO: Once Python 3.6 support drops, fix this.
# We're lying to Mypy here. That's not how the actual descriptor, even though it's
# somewhat close. But inheriting Generic implies not being final anymore in Python 3.6,
# until PEP 560, and internally there's no need for Generic.
class Const(Generic[T]):
    __slots__ = ()

    @overload
    def __get__(self,  # noqa: E704
                instance: 'Constants',
                owner: 'Type[Constants]') -> T: ...  # pragma: no cover

    @overload
    def __get__(self,  # noqa: E704
                instance: None,
                owner: 'Type[Constants]') -> 'Const[T]': ...  # pragma: no cover

    def __get__(self,
                instance: 'Optional[Constants]',
                owner: 'Type[Constants]') -> object:  # pragma: no cover
        pass


@API.private
@final
class MakeConst(metaclass=FinalMeta):
    def __call__(self,
                 __arg: Optional[object] = None,
                 *,
                 default: Any = Default.sentinel) -> Const[object]:
        # Not true yet, but will be changed by ConstantsMeta
        return cast(Const[object], LazyConstToDo(__arg, None, default))

    def __getitem__(self, tpe: Type[T]) -> 'MakeTypedConst[T]':
        return MakeTypedConst(tpe)


@API.private
@final
class MakeTypedConst(Immutable, Generic[T], metaclass=ImmutableGenericMeta):
    __slots__ = ('__type',)
    __type: Type[T]

    def __call__(self,
                 __arg: Optional[object] = None,
                 *,
                 default: Union[T, Default] = Default.sentinel) -> Const[T]:
        if not isinstance(default, (self.__type, Default)):
            raise TypeError(f"default is not an instance of {self.__type}, "
                            f"but {type(default)}")

        # Not true yet, but will be changed by ConstantsMeta
        return cast(Const[T], LazyConstToDo(__arg, self.__type, default))


@API.private
@final
class LazyConstToDo(FinalImmutable):
    __slots__ = ('arg', 'type_', 'default')
    arg: Optional[object]
    type_: Optional[type]
    default: object


@API.private
class ConstantsMeta(AbstractMeta):
    def __new__(mcs: 'Type[ConstantsMeta]',
                name: str,
                bases: Tuple[type, ...],
                namespace: Dict[str, object],
                **kwargs: object
                ) -> 'ConstantsMeta':
        cls = cast(
            ConstantsMeta,
            super().__new__(mcs, name, bases, namespace, **kwargs)  # type: ignore
        )
        if not kwargs.get('abstract'):
            _configure_constants(cls)
        return cls


@API.private
def _configure_constants(cls: ConstantsMeta) -> None:
    from .constants import Constants
    from .service import service

    conf = getattr(cls, '__antidote__', None)
    if not isinstance(conf, Constants.Conf):
        raise TypeError(f"Constants configuration (__antidote__) is expected to be a "
                        f"{Constants.Conf}, not a {type(conf)}")

    if conf.wiring is not None:
        conf.wiring.wire(cls)

    dependency: Hashable = service(cls, singleton=True)
    for name, v in list(cls.__dict__.items()):
        if isinstance(v, LazyConstToDo):
            setattr(cls,
                    name,
                    LazyConstDescriptor(
                        name=name,
                        dependency=dependency,
                        method_name=Constants.provide_const.__name__,
                        arg=v.arg,
                        default=v.default,
                        type_=v.type_ or object,
                        auto_cast=v.type_ is not None and v.type_ in conf.auto_cast))


@API.private
@final
class LazyConstDescriptor(FinalImmutable):
    __slots__ = ('name', 'dependency', 'method_name', 'arg', 'default', 'type_',
                 'auto_cast', '_cache')
    name: str
    dependency: Hashable
    method_name: str
    arg: object
    default: object
    type_: type
    auto_cast: bool
    _cache: str

    def __init__(self,
                 *,
                 name: str,
                 dependency: Hashable,
                 method_name: str,
                 arg: object,
                 default: object,
                 type_: type,
                 auto_cast: bool
                 ):
        assert isinstance(default, (Default, type_))
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

    def __get__(self, instance: object, owner: type) -> object:
        if instance is None:
            try:
                return getattr(owner, self._cache)
            except AttributeError:
                dependency = LazyConst(self)
                setattr(owner, self._cache, dependency)
                return dependency
        try:
            value = getattr(instance, self.method_name)(name=self.name,
                                                        arg=self.arg)
        except LookupError:
            if self.default is not Default.sentinel:
                return self.default
            raise

        if self.auto_cast:
            value = self.type_(value)

        if not isinstance(value, self.type_):
            raise TypeError(f"Constant {self.name} is not an instance of {self.type_}, "
                            f"but {type(value)}")

        return value


@API.private
@final
class LazyConst(FinalImmutable, Lazy):
    __slots__ = ('descriptor',)
    descriptor: LazyConstDescriptor

    def __init__(self, descriptor: LazyConstDescriptor) -> None:
        super().__init__(descriptor=descriptor)

    def debug_info(self) -> DependencyDebug:
        descriptor = cast(LazyConstDescriptor, self.descriptor)
        cls = cast(type, descriptor.dependency)
        return DependencyDebug(f"Const: {debug_repr(cls)}.{descriptor.name}",
                               scope=Scope.singleton(),
                               dependencies=[descriptor.dependency],
                               # TODO: Would be great if the first argument of the method
                               #       didn't show as unknown as it's always provided.
                               wired=[getattr(cls, descriptor.method_name)])

    def provide(self, container: Container) -> DependencyValue:
        # TODO: Waiting for a fix: https://github.com/python/mypy/issues/6910
        descriptor = cast(LazyConstDescriptor, self.descriptor)
        return DependencyValue(
            descriptor.__get__(
                container.get(descriptor.dependency),
                None  # type: ignore
            ),
            scope=Scope.singleton()
        )
