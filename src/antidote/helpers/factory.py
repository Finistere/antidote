import inspect
from typing import (Callable, cast, get_type_hints, Iterable, overload, TypeVar, Union)

from .register import register
from .wire import wire
from .._internal.default_container import get_default_container
from ..core import DEPENDENCIES_TYPE, DependencyContainer, inject
from ..exceptions import DuplicateDependencyError
from ..providers.factory import FactoryProvider
from ..providers.tag import Tag, TagProvider

F = TypeVar('F', Callable, type)


@overload
def factory(func: F,  # noqa: E704  # pragma: no cover
            *,
            auto_wire: Union[bool, Iterable[str]] = True,
            singleton: bool = True,
            dependencies: DEPENDENCIES_TYPE = None,
            use_names: Union[bool, Iterable[str]] = None,
            use_type_hints: Union[bool, Iterable[str]] = None,
            wire_super: Union[bool, Iterable[str]] = None,
            tags: Iterable[Union[str, Tag]] = None,
            container: DependencyContainer = None
            ) -> F: ...


@overload
def factory(*,  # noqa: E704  # pragma: no cover
            auto_wire: Union[bool, Iterable[str]] = True,
            singleton: bool = True,
            dependencies: DEPENDENCIES_TYPE = None,
            use_names: Union[bool, Iterable[str]] = None,
            use_type_hints: Union[bool, Iterable[str]] = None,
            wire_super: Union[bool, Iterable[str]] = None,
            tags: Iterable[Union[str, Tag]] = None,
            container: DependencyContainer = None
            ) -> Callable[[F], F]: ...


def factory(func: Union[Callable, type] = None,
            *,
            auto_wire: Union[bool, Iterable[str]] = True,
            singleton: bool = True,
            dependencies: DEPENDENCIES_TYPE = None,
            use_names: Union[bool, Iterable[str]] = None,
            use_type_hints: Union[bool, Iterable[str]] = None,
            wire_super: Union[bool, Iterable[str]] = None,
            tags: Iterable[Union[str, Tag]] = None,
            container: DependencyContainer = None
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
        wire_super: If a method from a super-class needs to be wired, specify
            either a list of method names or :code:`True` to enable it for
            all methods. Defaults to :code:`False`, only methods defined in the
            class itself can be wired.
        tags: Iterable of tag to be applied. Those must be either strings
            (the tag name) or :py:class:`~.providers.tag.Tag`. All
            dependencies with a specific tag can then be retrieved with
            a :py:class:`~.providers.tag.Tagged`.
        container: :py:class:`~.core.container.DependencyContainer` to which the
            dependency should be attached. Defaults to the global container,
            :code:`antidote.world`.

    Returns:
        object: The dependency_provider

    """
    container = container or get_default_container()

    def register_factory(obj):
        factory_provider = cast(FactoryProvider,
                                container.providers[FactoryProvider])

        if inspect.isclass(obj):
            if '__call__' not in dir(obj):
                raise TypeError("The class must implement __call__()")

            wire_raise_on_missing = True
            if auto_wire is None or isinstance(auto_wire, bool):
                if auto_wire is False:
                    methods = ()  # type: Iterable[str]
                else:
                    methods = ('__call__', '__init__')
                    wire_raise_on_missing = False
            else:
                methods = auto_wire

            if methods:
                obj = wire(obj,
                           methods=methods,
                           wire_super=wire_super,
                           raise_on_missing=wire_raise_on_missing,
                           dependencies=dependencies,
                           use_names=use_names,
                           use_type_hints=use_type_hints,
                           container=container)

            obj = register(obj, auto_wire=False, singleton=True, container=container)
            dependency = get_type_hints(obj.__call__).get('return')
            if dependency is None:
                raise ValueError("The return annotation is necessary on __call__."
                                 "It is used a the dependency.")
            factory_provider.register_providable_factory(
                dependency=dependency,
                singleton=singleton,
                takes_dependency=False,
                factory_dependency=obj
            )
        elif callable(obj):
            if auto_wire:
                obj = inject(obj,
                             dependencies=dependencies,
                             use_names=use_names,
                             use_type_hints=use_type_hints,
                             container=container)

            dependency = get_type_hints(obj).get('return')
            if dependency is None:
                raise ValueError("A return annotation is necessary."
                                 "It is used a the dependency.")
            factory_provider.register_factory(factory=obj,
                                              singleton=singleton,
                                              dependency=dependency,
                                              takes_dependency=False)
        else:
            raise TypeError("Must be either a function "
                            "or a class implementing __call__(), "
                            "not {!r}".format(type(obj)))

        if tags is not None:
            tag_provider = cast(TagProvider, container.providers[TagProvider])
            tag_provider.register(dependency=dependency,
                                  tags=tags)

        return obj

    return func and register_factory(func) or register_factory
