import functools
import inspect
import weakref
from collections import Mapping, Sequence
from typing import Any, Callable, Dict, Iterable, Type, Union, get_type_hints

from .container import DependencyContainer
from .injector import DependencyInjector
from .providers import FactoryProvider, ParameterProvider
from .utils import get_arguments_specification, rgetitem

ContainerAliasType = Union[Type[DependencyContainer], DependencyContainer]
InjectorAliasType = Union[Type[DependencyInjector], DependencyInjector]


class DependencyManager:
    """Provides utility functions/decorators to manage dependencies.

    Except for :py:meth:`attrib()` all functions can either be used as
    decorators or functions to directly modify an object.

    Custom instances or classes can be used as :py:attr:`container` and
    :py:attr:`injector`.

    """

    auto_wire = True  # type: bool
    """
    Default value for :code:`auto_wire` argument in methods such as
    :py:meth:`register()` or :py:meth:`factory()`
    """

    use_names = False  # type: bool
    """
    Default value for :code:`use_names` argument in methods such as
    :py:meth:`inject()` or :py:meth:`register()`
    """

    arg_map = None  # type: Dict
    """
    Default mapping for :code:`arg_map` argument in methods such as
    :py:meth:`inject()` or :py:meth:`register()`.
    """

    def __init__(self,
                 auto_wire: bool = None,
                 use_names: bool = None,
                 arg_map: Mapping = None,
                 container: ContainerAliasType = DependencyContainer,
                 injector: InjectorAliasType = DependencyInjector
                 ) -> None:
        """Initialize the DependencyManager.

        Args:
            auto_wire: Default value for :code:`auto_wire` argument.
            use_names: Default value for :code:`use_names` argument.
            container: Either an instance or the class of the container to use.
                Defaults to :py:class:`.DependencyContainer`.
            injector: Either an instance or the class of the injector to use.
                Defaults to :py:class:`.DependencyInjector`.
        """
        if auto_wire is not None:
            self.auto_wire = auto_wire
        if use_names is not None:
            self.use_names = use_names
        self.arg_map = dict()
        self.arg_map.update(arg_map or dict())

        self.container = (
            container() if isinstance(container, type) else container
        )  # type: DependencyContainer

        self.injector = (
            injector(self.container)
            if isinstance(injector, type) else
            injector
        )  # type: DependencyInjector
        self.container[DependencyInjector] = weakref.proxy(self.injector)

        self.provider(FactoryProvider, auto_wire=False)
        self._factories = (
            self.container.providers[FactoryProvider]
        )  # type: FactoryProvider
        self.provider(ParameterProvider, auto_wire=False)
        self._parameters = (
            self.container.providers[ParameterProvider]
        )  # type: ParameterProvider

    def __repr__(self):
        return (
            "{}(auto_wire={!r}, mapping={!r}, use_names={!r}, "
            "container={!r}, injector={!r})"
        ).format(
            type(self).__name__,
            self.auto_wire,
            self.arg_map,
            self.use_names,
            self.container,
            self.injector
        )

    def inject(self,
               func: Callable = None,
               arg_map: Union[Mapping, Sequence] = None,
               use_names: Union[bool, Iterable[str]] = None,
               bind: bool = False
               ) -> Callable:
        """Inject the dependency into the function.

        Args:
            func: Callable for which the argument should be injected.
            use_names: Whether the arguments name should be used to search for
                a dependency when no mapping, nor annotation is found.
            arg_map: Custom mapping of the arguments name to their respective
                dependency id. A sequence of dependencies can also be
                specified, arguments will be mapped automatically. Annotations
                are overriden.
            bind: bind arguments with functools.partial directly to avoid
                service retrieval overhead.

        Returns:
            callable: The injected function.

        """
        if use_names is None:
            use_names = self.use_names

        def _inject(f):

            _mapping = self.arg_map.copy()
            if isinstance(arg_map, Mapping):
                _mapping.update(arg_map)
            elif isinstance(arg_map, Sequence):
                arg_spec, _, _ = get_arguments_specification(f)
                for (name, _), dependency_id in zip(arg_spec, arg_map):
                    _mapping[name] = dependency_id

            if bind:
                return self.injector.bind(func=f, arg_map=_mapping,
                                          use_names=use_names)

            return self.injector.inject(func=f, arg_map=_mapping,
                                        use_names=use_names)

        return func and _inject(func) or _inject

    def register(self,
                 cls: type = None,
                 singleton: bool = True,
                 auto_wire: Union[bool, Iterable[str]] = None,
                 arg_map: Union[Mapping, Sequence] = None,
                 use_names: Union[bool, Iterable[str]] = None
                 ) -> Callable:
        """Register a dependency by its class.

        Args:
            cls: Object to register as a dependency.
            singleton: A singleton will be only be instantiated once. Otherwise
                the dependency will instantiated anew every time.
            auto_wire: Injects automatically the dependencies of the methods
                specified, or only of :code:`__init__()` if True.
            arg_map: Custom mapping of the arguments name to their respective
                dependency id. A sequence of dependencies can also be
                specified, arguments will be mapped automatically. Annotations
                are overriden.
            use_names: Whether the arguments name should be used to search for
                a dependency when no mapping, nor annotation is found.

        Returns:
            object: The dependency.

        """
        if auto_wire is None:
            auto_wire = self.auto_wire

        def register_class(_cls):
            if not inspect.isclass(_cls):
                raise ValueError(
                    "Expecting a class, found a {}".format(type(_cls))
                )

            if auto_wire:
                _cls = self.wire(
                    _cls,
                    methods=(
                        ('__init__',) if auto_wire is True else auto_wire
                    ),
                    arg_map=arg_map,
                    use_names=use_names
                )

            self._factories.register(dependency_id=_cls, factory=_cls,
                                     singleton=singleton)

            return _cls

        return cls and register_class(cls) or register_class

    def factory(self,
                func: Callable = None,
                dependency_id: Any = None,
                auto_wire: Union[bool, Iterable[str]] = None,
                singleton: bool = True,
                arg_map: Union[Mapping, Sequence] = None,
                use_names: Union[bool, Iterable[str]] = None,
                build_subclasses: bool = False
                ) -> Callable:
        """Register a dependency providers, a factory to build the dependency.

        Args:
            func: Callable which builds the dependency.
            dependency_id: Id of the dependency. Defaults to the
                dependency_provider.
            singleton: If True the dependency_provider is called only once.
                Otherwise it is called anew every time.
            auto_wire: Injects automatically the dependencies of the methods
                specified, or only of :code:`__init__()` and :code:`__call__()`
                if True. If True and the providers is a function, its arguments
                will be injected.
            arg_map: Custom mapping of the arguments name to their respective
                dependency id. A sequence of dependencies can also be
                specified, arguments will be mapped automatically. Annotations
                are overriden.
            use_names: Whether the arguments name should be used to search for
                a dependency when no mapping, nor annotation is found.
            build_subclasses: If True, subclasses will also be build with this
                factory. If multiple factories are defined, the first in the
                MRO is used.

        Returns:
            object: The dependency_provider

        """
        if auto_wire is None:
            auto_wire = self.auto_wire

        def register_factory(factory):
            if inspect.isclass(factory):
                if '__call__' not in dir(factory):
                    raise ValueError("Factory class needs to be callable.")
                type_hints = get_type_hints(factory.__call__) or {}

                if auto_wire:
                    factory = self.wire(
                        factory,
                        methods=(
                            ('__call__', '__init__')
                            if auto_wire is True else
                            auto_wire
                        ),
                        arg_map=arg_map,
                        use_names=use_names
                    )

                factory = factory()
            else:
                if not callable(factory):
                    raise ValueError("factory parameter needs to be callable.")
                type_hints = get_type_hints(factory) or {}

                if auto_wire:
                    factory = self.inject(factory,
                                          arg_map=arg_map,
                                          use_names=use_names)

            self._factories.register(
                factory=factory,
                singleton=singleton,
                dependency_id=dependency_id or type_hints.get('return'),
                build_subclasses=build_subclasses
            )
            return factory

        return func and register_factory(func) or register_factory

    def wire(self,
             cls: type = None,
             methods: Iterable[str] = None,
             **inject_kwargs) -> Callable:
        """Wire a class by injecting the dependencies in all specified methods.

        Args:
            cls: class to wire.
            methods: Name of the methods for which dependencies should be
                injected. Defaults to all defined methods.
            **inject_kwargs: Keyword arguments passed on to :py:meth:`inject`.

        Returns:
            type: Wired class.

        """

        def wire_methods(_cls):
            nonlocal methods

            if methods is None:
                methods = map(
                    lambda m: m[0],  # get only the name
                    inspect.getmembers(
                        _cls,
                        # Retrieve static methods, class methods, methods.
                        predicate=lambda f: (inspect.isfunction(f)
                                             or inspect.ismethod(f))
                    )
                )

            for method in methods:
                setattr(_cls,
                        method,
                        self.inject(getattr(_cls, method), **inject_kwargs))

            return _cls

        return cls and wire_methods(cls) or wire_methods

    def attrib(self,
               dependency_id=None,
               use_name: Union[bool, Iterable[str]] = None,
               **attr_kwargs
               ) -> Callable:
        """Injects a dependency with attributes defined with attrs package.

        Args:
            dependency_id: Id of the dependency to inject. Defaults to the
                annotation or attribute name if use_names.
            use_name: If True, use the attribute name to identify the
                dependency.
            **attr_kwargs: Keyword arguments passed on to attr.ib()

        Returns:
            object: attr.Attribute with a attr.Factory.

        """
        try:
            import attr
        except ImportError:
            raise RuntimeError("attrs package must be installed.")

        if use_name is None:
            use_name = self.use_names

        def factory(instance):
            nonlocal dependency_id

            if dependency_id is None:
                cls = instance.__class__
                type_hints = get_type_hints(cls) or {}

                for attribute in attr.fields(cls):
                    # Dirty way to find the attrib annotation.
                    # Maybe attr will eventually provide the annotation ?
                    if isinstance(attribute.default, attr.Factory) \
                            and attribute.default.factory is factory:
                        try:
                            dependency_id = type_hints[attribute.name]
                        except KeyError:
                            if use_name:
                                dependency_id = attribute.name
                                break
                        else:
                            break
                else:
                    raise ValueError(
                        "No dependency could be detected. Please specify "
                        "the parameter `dependency_id` or `use_name=True`."
                        "Annotations may also be used."
                    )

            return self.container[dependency_id]

        return attr.ib(default=attr.Factory(factory, takes_self=True),
                       **attr_kwargs)

    def provider(self,
                 cls: type = None,
                 auto_wire: Union[bool, Iterable[str]] = None,
                 arg_map: Union[Mapping, Sequence] = None,
                 use_names: Union[bool, Iterable[str]] = None
                 ):
        """Register a providers by its class.

        Args:
            cls: class to register as a providers.
            auto_wire: Injects automatically the dependencies of the methods
                specified, or only of :py:meth:`__init__` if True.
            arg_map : Custom mapping of the arguments name to their respective
                dependency id. A sequence of dependencies can also be
                specified, arguments will be mapped automatically. Annotations
                are overriden.
            use_names: Whether the arguments name should be used to search for
                a dependency when no mapping, nor annotation is found.

        Returns:
            type: the providers's class.
        """
        if auto_wire is None:
            auto_wire = self.auto_wire

        def register_provider(_cls):
            if not inspect.isclass(_cls):
                raise ValueError("Expecting a class, "
                                 "found {}".format(repr(type(_cls))))

            if not hasattr(_cls, '__antidote_provide__'):
                raise ValueError("Method __antidote_provide__() "
                                 "must be defined")

            if auto_wire:
                _cls = self.wire(
                    _cls,
                    methods=(
                        ('__init__',) if auto_wire is True else auto_wire
                    ),
                    arg_map=arg_map,
                    use_names=use_names
                )

            instance = _cls()
            instance.__antidote_provide__ = _ignore_arguments_excess(
                instance.__antidote_provide__
            )

            self.container.providers[_cls] = instance

            return _cls

        return cls and register_provider(cls) or register_provider

    def register_parameters(self,
                            data: Mapping,
                            getter: Union[Callable, str] = None,
                            prefix: str = '',
                            sep: str = '.'
                            ) -> Callable:
        """
        Register a mapping of parameters and its associated parser.

        Args:
            data: Mapping containing the parameters
            getter: Function which parses a dependency ID to an iterable of
                keys, used to recursively retrieve the parameter from the
                mapping. If no key can be parsed, :py:obj:`None` should be
                returned. For simplicity, if :code:`'split'` is specified, a
                parser is created which splits strings.
            prefix: If :code:`parser` is :code:`'split'`, only strings with
                the specified prefix will be taken into account.
            sep: If :code:`parser` is :code:`'split'`, dependency ids will be
                split by it.

        Returns:

        """

        def register_parser(f):
            if f == 'rgetitem':
                def f(obj, dependency_id):
                    if isinstance(dependency_id, str) \
                            and dependency_id.startswith(prefix):
                        return rgetitem(obj,
                                        dependency_id[len(prefix):].split(sep))

                    raise LookupError(dependency_id)

            elif callable(f):
                pass
            else:
                raise ValueError("parser must be callable or be 'getitem'")

            self._parameters.register(data, f)

            return f

        return getter and register_parser(getter) or register_parser


def _ignore_arguments_excess(func):
    """
    Decorate a function to ignore any additional arguments if it has no
    *args neither **kwargs.
    """
    arg_spec, has_var_args, has_var_kwargs = get_arguments_specification(func)

    if has_var_args and has_var_kwargs:
        return func

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Method is supposed to be bound (self is not in the arguments).
        if len(args) == 1 and not len(kwargs):
            return func(*args)

        new_kwargs = dict()

        if has_var_kwargs:
            new_kwargs = kwargs.copy()
        else:
            for name, _ in arg_spec:
                try:
                    new_kwargs[name] = kwargs[name]
                except KeyError:
                    pass

        if has_var_args:
            new_args = args
        else:
            new_args = []
            for (name, _), arg in zip(arg_spec, args):
                new_kwargs[name] = arg

        return func(*new_args, **new_kwargs)

    return wrapper
