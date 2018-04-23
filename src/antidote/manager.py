import inspect
import weakref
from collections import Mapping, Sequence
from functools import reduce
import contextlib
from typing import (
    Any, Callable, Dict, Iterable, TypeVar, Union, get_type_hints
)

from ._utils import get_arguments_specification
from .container import DependencyContainer
from .injector import DependencyInjector
from .providers import FactoryProvider, ParameterProvider

T = TypeVar('T')


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
                 container: DependencyContainer = None,
                 injector: DependencyInjector = None
                 ) -> None:
        """Initialize the DependencyManager.

        Args:
            auto_wire: Default value for :code:`auto_wire` argument.
            use_names: Default value for :code:`use_names` argument.
            container: Container to use if specified.
            injector: Injector to use if specified.

        """
        if auto_wire is not None:
            self.auto_wire = auto_wire
        if use_names is not None:
            self.use_names = use_names
        self.arg_map = dict()
        self.arg_map.update(arg_map or dict())

        self.container = container or DependencyContainer()
        self.container[DependencyContainer] = weakref.proxy(self.container)

        self.injector = injector or DependencyInjector(self.container)
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

    @property
    def providers(self):
        return self.container.providers

    def inject(self,
               func: Callable = None,
               arg_map: Union[Mapping, Sequence] = None,
               use_names: Union[bool, Iterable[str]] = None,
               bind: bool = False
               ) -> Callable:
        """Inject dependencies into the function.

        Args:
            func: Callable for which the argument should be injected.
            arg_map: Custom mapping of the arguments name to their respective
                dependency id. A sequence of dependencies can also be
                specified, which will be mapped to the arguments through their
                order. Annotations are overriden.
            use_names: Whether the arguments name should be used to find for
                a dependency. An iterable of names may also be provided to
                restrict this to a subset of the arguments. Annotations are
                overriden, but not the arg_map.
            bind: bind arguments with :py:func:`functools.partial` directly to
                avoid the overhead of retrieving dependencies. This should only
                be used when necessary, it makes testing a lot more difficult.

        Returns:
            The injected function or a decorator.

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
                 ) -> Union[Callable, type]:
        """Register a dependency by its class.

        Args:
            cls: Class to register as a dependency. It will be instantiated
                only when requested.
            singleton: If True, the class will be instantiated only once,
                further will receive the same instance.
            auto_wire: Injects automatically the dependencies of the methods
                specified, or only of :code:`__init__()` if True.
            arg_map: Custom mapping of the arguments name to their respective
                dependency id. A sequence of dependencies can also be
                specified, which will be mapped to the arguments through their
                order. Annotations are overriden.
            use_names: Whether the arguments name should be used to find for
                a dependency. An iterable of names may also be provided to
                restrict this to a subset of the arguments. Annotations are
                overriden, but not the arg_map.

        Returns:
            The class or the class decorator.

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
            dependency_id: Id of the dependency. Defaults to the return type of
                :code:`func` if specified.
            singleton: If True the dependency_provider is called only once.
                Otherwise it is called anew every time.
            auto_wire: If :code:`func` is a function, its dependencies are
                injected if True. Should :code:`func` be a class with
                :py:func:`__call__`, dependencies of :code:`__init__()` and
                :code:`__call__()` will be injected if True. One may also
                provide an iterable of method names requiring dependency
                injection.
            arg_map: Custom mapping of the arguments name to their respective
                dependency id. A sequence of dependencies can also be
                specified, which will be mapped to the arguments through their
                order. Annotations are overriden.
            use_names: Whether the arguments name should be used to find for
                a dependency. An iterable of names may also be provided to
                restrict this to a subset of the arguments. Annotations are
                overriden, but not the arg_map.
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
             **inject_kwargs
             ) -> Union[Callable, type]:
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
               dependency_id: Any = None,
               use_name: bool = None,
               **attr_kwargs
               ):
        """Injects a dependency with attributes defined with attrs package.

        Args:
            dependency_id: Id of the dependency to inject. Defaults to the
                annotation.
            use_name: If True, use the attribute name as the dependency id
                overriding any annotations.
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
                 ) -> Union[Callable, type]:
        """Register a providers by its class.

        Args:
            cls: class to register as a provider. The class must have a
                :code:`__antidote_provide()` method accepting as first argument
                the dependency id. Variable keyword and positional arguments
                must be accepted as they may be provided.
            auto_wire: If True, the dependencies of :code:`__init__()` are
                injected. An iterable of method names which require dependency
                injection may also be specified.
            arg_map: Custom mapping of the arguments name to their respective
                dependency id. A sequence of dependencies can also be
                specified, which will be mapped to the arguments through their
                order. Annotations are overriden.
            use_names: Whether the arguments name should be used to find for
                a dependency. An iterable of names may also be provided to
                restrict this to a subset of the arguments. Annotations are
                overriden, but not the arg_map.

        Returns:
            the providers's class or the class decorator.
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

            self.container.providers[_cls] = _cls()

            return _cls

        return cls and register_provider(cls) or register_provider

    def register_parameters(self,
                            parameters: T,
                            getter: Union[Callable[[T, Any], Any], str] = None,
                            prefix: str = '',
                            split: str = ''
                            ) -> Callable:
        """
        Register a mapping of parameters and its associated parser.

        Args:
            parameters: Object containing the parameters, usually a mapping.
            getter: Function retrieving the dependency from the parameters, it
                must accept the parameters as first argument and the dependency
                id as second.
            prefix: If specified, only string prefixed with it will be taken
                into account.
            split: If specified, only string dependency_id are accepted, which
                will be split by :code:`split`. The result is used to
                recursively retrieve the dependency from :code:`parameters`.
                Beware that :py:exc:`TypeError` will be converted to
                :py:exc:`LookUpError` and thus be ignored, as the recursion may
                go too far.

        Returns:
            getter callable or decorator.
        """
        if not isinstance(prefix, str) or not isinstance(split, str):
            raise ValueError("prefix and split arguments must be strings.")

        def register_parser(f):
            if not callable(f):
                raise ValueError("parser must be callable or be 'getitem'")

            if prefix or split:
                def _getter(params, dependency_id):
                    if not isinstance(dependency_id, str) \
                            or not dependency_id.startswith(prefix):
                        raise LookupError(dependency_id)

                    dependency_id = dependency_id[len(prefix):]

                    if split:
                        try:
                            return reduce(f, dependency_id.split(split),
                                          params)
                        except TypeError as e:
                            raise LookupError(dependency_id) from e

                    return f(params, dependency_id)
            else:
                _getter = f

            self._parameters.register(parameters, _getter)

            return f

        return getter and register_parser(getter) or register_parser

    @contextlib.contextmanager
    def context(self,
                dependencies: Union[Mapping, Iterable] = None,
                include: Iterable = None,
                exclude: Iterable = None,
                missing: Iterable = None
                ):
        """
        Creates a context within one can control which of the defined
        dependencies available or not. Any changes will be discarded at the
        end.

        >>> from antidote import antidote, DependencyContainer
        >>> with antidote.context(include=[]):
        ...     s = 'Your code isolated from every other dependencies'
        ...     antidote.container[DependencyContainer]
        <... DependencyContainer ...>

        The :py:class:`~antidote.DependencyInjector` and the
        :py:class:`~antidote.DependencyContainer` will still be accessible.

        Args:
            dependencies: Dependencies instances used to override existing ones
                in the new context.
            include: Iterable of dependency to include. If None
                everything is accessible.
            exclude: Iterable of dependency to exclude.
            missing: Iterable of dependency which should raise a
                :py:exc:`~.exceptions.DependencyNotFoundError` even if a
                provider could instantiate them.

        """
        with self.container.context(dependencies=dependencies, include=include,
                                    exclude=exclude, missing=missing):
            # Re-inject DependencyManager's globals
            self.container[DependencyContainer] = weakref.proxy(self.container)
            self.container[DependencyInjector] = weakref.proxy(self.injector)
            yield
