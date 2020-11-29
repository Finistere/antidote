import weakref
from typing import Callable, TYPE_CHECKING, Union

from ._compatibility.typing import final
from ._internal import API
from ._internal.utils import debug_repr, FinalImmutable
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
    func: Callable
    singleton: bool
    args: tuple
    kwargs: dict

    def __antidote_debug_repr__(self):
        return f"LazyCall(func={debug_repr(self.func)}, " \
               f"args={self.args}, kwargs={self.kwargs}" \
               f"singleton={self.singleton})"

    def debug_info(self) -> DependencyDebug:
        return DependencyDebug(
            f"Lazy '{debug_repr(self.func)}' "
            f"with args={self.args!r} and kwargs={self.kwargs!r}",
            singleton=self.singleton,
            wired=[self.func])

    def lazy_get(self, container: Container) -> DependencyInstance:
        return DependencyInstance(self.func(*self.args, **self.kwargs), self.singleton)


@API.private
@final
class LazyMethodCallWithArgsKwargs(FinalImmutable, copy=False):
    """
    :meta private:
    """
    __slots__ = ('method_name', 'singleton', '_cache_attr', 'args', 'kwargs')
    method_name: str
    singleton: bool
    args: tuple
    kwargs: dict
    _cache_attr: str

    def __get__(self, instance, owner):
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

    def __str__(self):
        return f"Lazy Method '{self.method_name}' " \
               f"with args={self.args} and kwargs={self.kwargs}"


@API.private
@final
class LazyMethodCallDependency(FinalImmutable, Lazy):
    """
    :meta private:
    """
    __slots__ = ('descriptor', 'owner_ref', 'singleton')
    descriptor: 'Union[LazyMethodCall, LazyMethodCallWithArgsKwargs]'
    owner_ref: weakref.ReferenceType
    singleton: bool

    def debug_info(self) -> DependencyDebug:
        owner = self.owner_ref()
        assert owner is not None
        method = self.descriptor.method_name
        return DependencyDebug(str(self.descriptor),
                               singleton=self.descriptor.singleton,
                               wired=[getattr(owner, method)],
                               dependencies=[owner])

    def lazy_get(self, container: Container) -> DependencyInstance:
        owner = self.owner_ref()
        assert owner is not None
        return DependencyInstance(
            self.descriptor.__get__(container.get(owner), owner),
            self.singleton
        )
