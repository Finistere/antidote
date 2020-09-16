import inspect
from typing import (Any, Callable, get_type_hints, Iterable, Optional, overload, Protocol,
                    TypeVar,
                    Union)

from ._definitions import Dependency
from ._factory import FactoryMeta, LambdaFactory, PreBuild
from .inject import DEPENDENCIES_TYPE, inject
from .register import register
from .wire import wire, Wiring
from .._internal.utils import API
from ..providers.factory import Build, FactoryProvider
from ..providers.tag import Tag, TagProvider

F = TypeVar('F', bound=Callable[..., Any])


class FactoryProtocol(Protocol):
    def __rmatmul__(self, dependency) -> Build:
        pass

    def with_kwargs(self, **kwargs) -> PreBuild:
        pass

    __call__: F


@API.public
class Factory(metaclass=FactoryMeta):
    # Both __call__() and __init__() will be injected with default parameters.
    wiring: Optional[Wiring] = Wiring.auto()
    singleton: bool = True
    tags: Iterable[Union[str, Tag]] = None

    __antidote__ = Dependency(wiring=Wiring.auto(), singleton=True, tags=None)


@overload
def factory(func: F,  # noqa: E704  # pragma: no cover
            singleton: bool = True,
            tags: Iterable[Union[str, Tag]] = None
            ) -> FactoryProtocol[F]: ...


@overload
def factory(*,  # noqa: E704  # pragma: no cover
            singleton: bool = True,
            tags: Iterable[Union[str, Tag]] = None
            ) -> Callable[[F], FactoryProtocol[F]]: ...


@API.public
def factory(func: F = None,
            *,
            auto_wire: bool = True,
            singleton: bool = True,
            dependencies: DEPENDENCIES_TYPE = None,
            use_names: Union[bool, Iterable[str]] = None,
            use_type_hints: Union[bool, Iterable[str]] = None,
            tags: Iterable[Union[str, Tag]] = None
            ):
    """Register a dependency providers, a factory to build the dependency.

    Args:
        func: Callable which builds the dependency.
        singleton: If True, `func` will only be called once. If not it is
            called at each injection.
        auto_wire: If :code:`func` is a function, its dependencies are
            injected if True. Should :code:`func` be a class with
            :py:func:`__call__`, dependencies of :code:`__init__()` and
            :code:`__call__()` will be injected if True. One may also
            provide an iterable of method names requiring dependency
            injection.
        dependencies: Can be either a mapping of arguments name to their
            dependency, an iterable of dependencies or a function which returns
            the dependency given the arguments name. If an iterable is specified,
            the position of the arguments is used to determine their respective
            dependency. An argument may be skipped by using :code:`None` as a
            placeholder. The first argument is always ignored for methods (self)
            and class methods (cls).Type hints are overridden. Defaults to :code:`None`.
        use_names: Whether or not the arguments' name should be used as their
            respective dependency. An iterable of argument names may also be
            supplied to restrict this to those. Defaults to :code:`False`.
        use_type_hints: Whether or not the type hints (annotations) should be
            used as the arguments dependency. An iterable of argument names may
            also be specified to restrict this to those. Any type hints from
            the builtins (str, int...) or the typing (:py:class:`~typing.Optional`,
            ...) are ignored. Defaults to :code:`True`.
        tags: Iterable of tag to be applied. Those must be either strings
            (the tag name) or :py:class:`~.providers.tag.Tag`. All
            dependencies with a specific tag can then be retrieved with
            a :py:class:`~.providers.tag.Tagged`.

    Returns:
        object: The dependency_provider

    """

    @inject
    def register_factory(func,
                         factory_provider: FactoryProvider,
                         tag_provider: TagProvider = None):
        if inspect.isfunction(func):
            dependency = get_type_hints(func).get('return')
            if dependency is None:
                raise ValueError("A return annotation is necessary. "
                                 "It is used a the dependency.")

            if auto_wire:
                func = inject(func,
                              dependencies=dependencies,
                              use_names=use_names,
                              use_type_hints=use_type_hints)

            factory_provider.register_factory(factory=LambdaFactory(func),
                                              singleton=singleton,
                                              dependency=dependency,
                                              takes_dependency=False)
        else:
            raise TypeError(f"{func} is not a function")

        if tags is not None:
            if tag_provider is None:
                raise RuntimeError("No TagProvider registered, cannot use tags.")
            tag_provider.register(dependency=dependency, tags=tags)

        return func

    return func and register_factory(func) or register_factory
