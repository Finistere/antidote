import collections.abc as c_abc
import inspect
from typing import Any, Callable, cast, Iterable, overload, TypeVar, Union

from .wire import wire
from .._internal.default_container import get_default_container
from ..core import DEPENDENCIES_TYPE, DependencyContainer, inject
from ..providers.factory import FactoryProvider
from ..providers.tag import Tag, TagProvider

C = TypeVar('C', bound=type)


@overload
def register(class_: C,  # noqa: E704  # pragma: no cover
             *,
             singleton: bool = True,
             factory: Union[Callable, str] = None,
             factory_dependency: Any = None,
             auto_wire: Union[bool, Iterable[str]] = None,
             dependencies: DEPENDENCIES_TYPE = None,
             use_names: Union[bool, Iterable[str]] = None,
             use_type_hints: Union[bool, Iterable[str]] = None,
             wire_super: Union[bool, Iterable[str]] = None,
             tags: Iterable[Union[str, Tag]] = None,
             container: DependencyContainer = None
             ) -> C: ...


@overload
def register(*,  # noqa: E704  # pragma: no cover
             singleton: bool = True,
             factory: Union[Callable, str] = None,
             factory_dependency: Any = None,
             auto_wire: Union[bool, Iterable[str]] = None,
             dependencies: DEPENDENCIES_TYPE = None,
             use_names: Union[bool, Iterable[str]] = None,
             use_type_hints: Union[bool, Iterable[str]] = None,
             wire_super: Union[bool, Iterable[str]] = None,
             tags: Iterable[Union[str, Tag]] = None,
             container: DependencyContainer = None
             ) -> Callable[[C], C]: ...


def register(class_=None,
             *,
             singleton: bool = True,
             factory: Union[Callable, str] = None,
             factory_dependency: Any = None,
             auto_wire: Union[bool, Iterable[str]] = None,
             dependencies: DEPENDENCIES_TYPE = None,
             use_names: Union[bool, Iterable[str]] = None,
             use_type_hints: Union[bool, Iterable[str]] = None,
             wire_super: Union[bool, Iterable[str]] = None,
             tags: Iterable[Union[str, Tag]] = None,
             container: DependencyContainer = None):
    """Register a dependency by its class.

    Args:
        class_: Class to register as a dependency. It will be instantiated
            only when requested.
        singleton: If True, the class will be instantiated only once,
            further will receive the same instance.
        factory: Callable to be used when building the class, this allows to
            re-use the same factory for subclasses for example. The dependency
            is given as first argument. If a string is specified, it is
            interpreted as the name of the method which has to be used to build
            the class. The class is given as first argument for static methods
            but not for class methods. Cannot be used together with
            :code:`factory_dependency`.
        factory_dependency: If specified Antidote will retrieve the factory in
            the container with it. The class is given as first argument. Cannot
            be used together with :code:`factory`.
        auto_wire: Injects automatically the dependencies of the methods
            specified, or only of :code:`__init__()` if True.
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
        The class or the class decorator.

    """
    if factory is not None and factory_dependency is not None:
        raise ValueError("factory and factory_dependency cannot be used together.")

    if not (factory is None or isinstance(factory, str) or inspect.isfunction(factory)):
        raise TypeError("factory must be either None, a method name or a function "
                        "not {!r}".format(type(factory)))

    container = container or get_default_container()
    auto_wire = auto_wire if auto_wire is not None else True
    methods = ()  # type: Iterable[str]
    wire_raise_on_missing = True

    if isinstance(auto_wire, bool):  # for Mypy
        if auto_wire:
            if isinstance(factory, str):
                methods = (factory,)
                if wire_super is None:
                    wire_super = (factory,)
            elif factory is None:
                wire_raise_on_missing = False
                methods = ('__init__',)
    else:
        methods = auto_wire

    def register_service(cls):
        nonlocal factory

        if not inspect.isclass(cls):
            raise TypeError("Expected a class, got {!r}".format(cls))

        takes_dependency = False
        if isinstance(factory, str):
            static_factory = inspect.getattr_static(cls, factory)
            if not isinstance(static_factory, (staticmethod, classmethod)):
                raise TypeError("Only class methods and static methods "
                                "are supported as factories. Not "
                                "{!r}".format(static_factory))
            if isinstance(static_factory, staticmethod):
                takes_dependency = True

        if auto_wire:
            cls = wire(cls,
                       methods=methods,
                       wire_super=wire_super,
                       dependencies=dependencies,
                       use_names=use_names,
                       use_type_hints=use_type_hints,
                       container=container,
                       raise_on_missing=wire_raise_on_missing)

        if isinstance(factory, str):
            # Retrieve injected class/static method
            factory = cast(Callable, getattr(cls, factory))
        elif inspect.isfunction(factory):
            takes_dependency = True
            if not isinstance(dependencies, c_abc.Mapping) \
                    and isinstance(dependencies, c_abc.Iterable):
                # takes dependency as first argument
                factory_dependencies = (None,) + tuple(dependencies)
            else:
                factory_dependencies = dependencies

            if auto_wire:
                factory = inject(factory,
                                 dependencies=factory_dependencies,
                                 use_names=use_names,
                                 use_type_hints=use_type_hints,
                                 container=container)

        factory_provider = cast(FactoryProvider, container.providers[FactoryProvider])
        if factory is not None:
            factory_provider.register_factory(
                dependency=cls,
                factory=factory,
                singleton=singleton,
                takes_dependency=takes_dependency)
        elif factory_dependency is not None:
            factory_provider.register_providable_factory(
                dependency=cls,
                factory_dependency=factory_dependency,
                singleton=singleton,
                takes_dependency=True)
        else:
            factory_provider.register_class(cls, singleton=singleton)

        if tags is not None:
            tag_provider = cast(TagProvider, container.providers[TagProvider])
            tag_provider.register(cls, tags)

        return cls

    return class_ and register_service(class_) or register_service
