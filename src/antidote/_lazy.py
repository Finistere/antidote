import weakref
from typing import Callable, cast, Dict, Tuple, Type, TYPE_CHECKING, Union

from ._compatibility.typing import final
from ._internal import API
from ._internal.utils import debug_repr, FinalImmutable, short_id
from ._providers import Lazy
from .core import Container, DependencyInstance
from .core.utils import DependencyDebug

if TYPE_CHECKING:
    from .lazy import LazyMethodCall


@API.private
@final
class LazyCallWithArgsKwargs(FinalImmutable, Lazy):
    """
    :meta private:
    """
    __slots__ = ('func', 'singleton', 'args', 'kwargs')
    func: Callable[..., object]
    singleton: bool
    args: Tuple[object, ...]
    kwargs: Dict[str, object]

    def __antidote_debug_repr__(self) -> str:
        s = f"Lazy: {debug_repr(self.func)}(*{self.args}, **{self.kwargs})"
        if self.singleton:
            s += f"  #{short_id(self)}"
        return s

    def debug_info(self) -> DependencyDebug:
        return DependencyDebug(self.__antidote_debug_repr__(),
                               singleton=self.singleton,
                               wired=[self.func])

    def lazy_get(self, container: Container) -> DependencyInstance:
        return DependencyInstance(self.func(*self.args, **self.kwargs),
                                  singleton=self.singleton)


@API.private
@final
class LazyMethodCallWithArgsKwargs(FinalImmutable):
    """
    :meta private:
    """
    __slots__ = ('method_name', 'singleton', 'args', 'kwargs', '_cache_attr')
    method_name: str
    singleton: bool
    args: Tuple[object, ...]
    kwargs: Dict[str, object]
    _cache_attr: str

    def __init__(self, method_name: str, singleton: bool, args: Tuple[object, ...],
                 kwargs: Dict[str, object]) -> None:
        super().__init__(method_name, singleton, args, kwargs,
                         f"__antidote_dependency_{hex(id(self))}")

    def __get__(self, instance: object, owner: type) -> object:
        if instance is None:
            try:
                return getattr(owner, self._cache_attr)
            except AttributeError:
                dependency = LazyMethodCallDependency(self,
                                                      weakref.ref(owner),
                                                      self.singleton)
                setattr(owner, self._cache_attr, dependency)
                return dependency
        return getattr(instance, self.method_name)(*self.args, **self.kwargs)

    def __str__(self) -> str:
        s = f"Lazy Method: {self.method_name}(*{self.args}, **{self.kwargs})"
        if self.singleton:
            s += f"  #{short_id(self)}"
        return s


@API.private
@final
class LazyMethodCallDependency(FinalImmutable, Lazy):
    """
    :meta private:
    """
    __slots__ = ('descriptor', 'owner_ref', 'singleton')
    descriptor: 'Union[LazyMethodCall, LazyMethodCallWithArgsKwargs]'
    owner_ref: 'weakref.ReferenceType[type]'
    singleton: bool

    def debug_info(self) -> DependencyDebug:
        owner = self.owner_ref()
        assert owner is not None
        descriptor = cast('LazyMethodCall', self.descriptor)
        return DependencyDebug(str(descriptor),
                               singleton=descriptor.singleton,
                               wired=[getattr(owner, descriptor.method_name)],
                               dependencies=[owner])

    def lazy_get(self, container: Container) -> DependencyInstance:
        owner = self.owner_ref()
        assert owner is not None
        descriptor = cast('LazyMethodCall', self.descriptor)
        return DependencyInstance(descriptor.__get__(container.get(owner), owner),
                                  singleton=self.singleton)