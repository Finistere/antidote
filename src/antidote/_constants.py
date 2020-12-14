from typing import Any, Callable, cast, Dict, Hashable, Optional, Tuple, Type, TypeVar

from ._compatibility.typing import final
from ._internal import API
from ._internal.utils import AbstractMeta, FinalImmutable, FinalMeta
from ._providers.lazy import FastLazyConst

T = TypeVar('T')

_CONST_CONSTRUCTOR_METHOD = 'get'


@API.private
@final
class MakeConst(metaclass=FinalMeta):
    def __call__(self, value: Any) -> Any:
        # Not true yet, but will be changed by ConstantsMeta
        return LazyConstToDo(value, None)

    def __getitem__(self, tpe: Type[T]) -> Callable[[Any], T]:
        def f(value: Any) -> T:
            return cast(T, LazyConstToDo(value, tpe))

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

    method = getattr(cls, _CONST_CONSTRUCTOR_METHOD, None)
    if method is None:
        raise TypeError(
            f"{cls} does not implement the lazy method '{_CONST_CONSTRUCTOR_METHOD}'")

    if conf.wiring is not None:
        conf.wiring.wire(cls)

    if conf.public:
        dependency: Hashable = service(cls, singleton=True)
    else:
        dependency = LazyCall(cls, singleton=True)

    # TODO: Waiting for a fix: https://github.com/python/mypy/issues/6910
    is_const = cast(Callable[[str], bool], getattr(conf, 'is_const'))
    for name, v in list(cls.__dict__.items()):
        if isinstance(v, LazyConstToDo):
            setattr(cls,
                    name,
                    LazyConst(name,
                              dependency,
                              _CONST_CONSTRUCTOR_METHOD,
                              v.value,
                              v.type_ if v.type_ in conf.auto_cast else None))
        elif is_const(name):
            setattr(cls, name, LazyConst(name,
                                         dependency,
                                         _CONST_CONSTRUCTOR_METHOD,
                                         v))


Cast = Callable[[object], object]


@API.private
@final
class LazyConst(FinalImmutable):
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
                dependency = FastLazyConst(self.name,
                                           self.dependency,
                                           self.method_name,
                                           self.value,
                                           _cast)
                setattr(owner, self._cache, dependency)
                return dependency
        _cast = cast(Cast, getattr(self, 'cast'))
        return _cast(getattr(instance, self.method_name)(self.value))
