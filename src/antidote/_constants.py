from typing import (Any, Callable, cast, Dict, Generic, Hashable, Optional, Tuple, Type,
                    TypeVar)

from ._compatibility.typing import final
from ._internal import API
from ._internal.utils import AbstractMeta, debug_repr, FinalImmutable, FinalMeta
from ._providers.lazy import Lazy
from .core import Container, DependencyInstance
from .core.utils import DependencyDebug

T = TypeVar('T')

_CONST_CONSTRUCTOR_METHOD = 'get'


class Const(Generic[T]):
    def __get__(self, instance: Any, owner: Any) -> T:  # pragma: no cover
        pass


@API.private
@final
class MakeConst(metaclass=FinalMeta):
    def __call__(self, value: object) -> Const[T]:
        # Not true yet, but will be changed by ConstantsMeta
        return cast(Const[T], LazyConstToDo(value, None))

    def __getitem__(self, tpe: Type[T]) -> Callable[[object], Const[T]]:
        def f(value: object) -> Const[T]:
            return cast(Const[T], LazyConstToDo(value, tpe))

        return f


@API.private
@final
class LazyConstToDo(FinalImmutable):
    __slots__ = ('value', 'type_')
    value: object
    type_: Optional[type]


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
    from .lazy import LazyCall
    from .service import service

    conf = getattr(cls, '__antidote__', None)
    if not isinstance(conf, Constants.Conf):
        raise TypeError(f"Constants configuration (__antidote__) is expected to be a "
                        f"{Constants.Conf}, not a {type(conf)}")

    if conf.wiring is not None:
        conf.wiring.wire(cls)

    if conf.public:
        dependency: Hashable = service(cls, singleton=True)
    else:
        dependency = LazyCall(cls, singleton=True)

    for name, v in list(cls.__dict__.items()):
        if isinstance(v, LazyConstToDo):
            setattr(cls,
                    name,
                    LazyConstDescriptor(name,
                                        dependency,
                                        _CONST_CONSTRUCTOR_METHOD,
                                        v.value,
                                        v.type_ if v.type_ in conf.auto_cast else None))


Cast = Callable[[object], object]


@API.private
@final
class LazyConstDescriptor(FinalImmutable):
    __slots__ = ('name', 'dependency', 'method_name', 'value', 'cast', '_cache')
    name: str
    dependency: Hashable
    method_name: str
    value: object
    cast: Cast
    _cache: str

    def __init__(self, name: str, dependency: Hashable, method_name: str, value: object,
                 cast: Cast = None):
        super().__init__(
            name=name,
            dependency=dependency,
            method_name=method_name,
            value=value,
            cast=cast or (lambda x: x),
            _cache=f"__antidote_dependency_{hex(id(self))}"
        )

    def __get__(self, instance: object, owner: type) -> object:
        if instance is None:
            try:
                return getattr(owner, self._cache)
            except AttributeError:
                # TODO: Waiting for a fix: https://github.com/python/mypy/issues/6910
                _cast = cast(Cast, getattr(self, 'cast'))
                dependency = LazyConst(self)
                setattr(owner, self._cache, dependency)
                return dependency
        _cast = cast(Cast, getattr(self, 'cast'))
        return _cast(getattr(instance, self.method_name)(self.value))


@API.private
@final
class LazyConst(FinalImmutable, Lazy):
    __slots__ = ('descriptor',)
    descriptor: LazyConstDescriptor

    def __init__(self, descriptor: LazyConstDescriptor) -> None:
        super().__init__(descriptor=descriptor)

    def debug_info(self) -> DependencyDebug:
        from .lazy import LazyCall
        descriptor = cast(LazyConstDescriptor, self.descriptor)
        dependency = descriptor.dependency
        if isinstance(dependency, LazyCall):
            cls: type = cast(type, dependency.func)
        else:
            cls = cast(type, dependency)
        return DependencyDebug(f"Const: {debug_repr(cls)}.{descriptor.name}",
                               singleton=True,
                               dependencies=[dependency],
                               # TODO: Would be great if the first argument of the method
                               #       didn't show as unknown as it's always provided.
                               wired=[getattr(cls, descriptor.method_name)])

    def lazy_get(self, container: Container) -> DependencyInstance:
        # TODO: Waiting for a fix: https://github.com/python/mypy/issues/6910
        descriptor = cast(LazyConstDescriptor, self.descriptor)
        return DependencyInstance(
            descriptor.__get__(
                container.get(descriptor.dependency),
                None  # type: ignore
            ),
            singleton=True
        )
