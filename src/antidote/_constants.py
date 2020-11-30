from typing import Any, Callable, cast, Type, TypeVar

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
        return LazyConstToDo(value, )

    def __getitem__(self, tpe: Type[T]) -> Callable[[Any], T]:
        def f(value: Any) -> T:
            return cast(T, LazyConstToDo(value, ))

        return f


@API.private
@final
class LazyConstToDo(FinalImmutable):
    __slots__ = ('value',)
    value: object


@API.private
class ConstantsMeta(AbstractMeta):
    def __new__(mcls, name, bases, namespace, **kwargs):
        cls = super().__new__(mcls, name, bases, namespace, **kwargs)
        if not kwargs.get('abstract'):
            _configure_constants(cls)
        return cls


@API.private
def _configure_constants(cls):
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
        dependency = service(cls, singleton=True)
    else:
        dependency = LazyCall(cls, singleton=True)

    # Waiting for a fix: https://github.com/python/mypy/issues/6910
    is_const = cast(Callable[[str], bool], getattr(conf, 'is_const'))
    for name, v in list(cls.__dict__.items()):
        if isinstance(v, LazyConstToDo):
            setattr(cls, name, LazyConst(dependency, _CONST_CONSTRUCTOR_METHOD, v.value))
        elif is_const(name):
            setattr(cls, name, LazyConst(dependency, _CONST_CONSTRUCTOR_METHOD, v))


@API.private
@final
class LazyConst(FinalImmutable, copy=False):
    __slots__ = ('dependency', 'method_name', 'value', '_cache')
    dependency: object
    method_name: str
    value: object
    _cache: str

    def __init__(self, dependency, method_name: str, value):
        super().__init__(
            dependency=dependency,
            method_name=method_name,
            value=value,
            _cache=f"__antidote_dependency_{hex(id(self))}"
        )

    def __get__(self, instance, owner):
        if instance is None:
            try:
                return getattr(owner, self._cache)
            except AttributeError:
                dependency = FastLazyConst(self.dependency,
                                           self.method_name,
                                           self.value)
                setattr(owner, self._cache, dependency)
                return dependency
        return getattr(instance, self.method_name)(self.value)
