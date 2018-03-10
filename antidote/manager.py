import inspect
from typing import Any, Callable, Dict, Iterable, Type, Union, get_type_hints

import weakref
import wrapt
from past.builtins import basestring

from ._compat import PY3, get_arguments_specification
from .container import DependencyContainer
from .injection import DependencyInjector
from .providers import FactoryProvider, ParameterProvider

try:
    from configparser import RawConfigParser, NoOptionError, NoSectionError
except ImportError:
    from ConfigParser import RawConfigParser  # type: ignore
    from ConfigParser import NoOptionError  # type: ignore
    from ConfigParser import NoSectionError  # type: ignore


class DependencyManager(object):
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

    mapping = None  # type: Dict
    """
    Default mapping for :code:`mapping` argument in methods such as
    :py:meth:`inject()` or :py:meth:`register()`.
    """

    def __init__(self,
                 auto_wire=None,  # type: bool
                 use_names=None,  # type: bool
                 mapping=None,  # type: Dict
                 container=DependencyContainer,
                 # type: Type[DependencyContainer]
                 injector=DependencyInjector  # type: Type[DependencyInjector]
                 ):
        # type: (...) -> None
        """Initialize the DependencyManager.

        Args:
            auto_wire (bool, optional): Default value for :code:`auto_wire`
                argument. Defaults to True.
            use_names (bool, optional): Default value for
                :code:`use_names` argument. Defaults to False.
            container (type or object, optional): Either an instance or the
                class of the container to use. Defaults to
                :py:class:`.DependencyContainer`.
            injector (type or object, optional): Either an instance or the
                class of the injector to use. Defaults to
                :py:class:`.DependencyInjector`.
        """
        if auto_wire is not None:
            self.auto_wire = auto_wire
        if use_names is not None:
            self.use_names = use_names
        self.mapping = mapping or dict()

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

    def inject(self,
               func=None,  # type: Callable
               mapping=None,  # type: Dict
               use_names=None,   # type: Union[bool, Iterable[str]]
               bind=False  # type: bool
               ):
        # type: (...) -> Callable
        """Inject the dependency into the function.

        Args:
            func (callable): Callable for which the argument should be
                injected.
            use_names (bool, optional): Whether the arguments name
                should be used to search for a dependency when no mapping,
                nor annotation is found. Defaults to False.
            mapping (dict, optional): Custom mapping of the arguments name
                to their respective dependency id. Overrides annotations.
                Defaults to None.
            bind (bool, optional): bind arguments with functools.partial
                directly to avoid service retrieval overhead. Defaults to
                False.

        Returns:
            callable: The injected function.

        """
        if use_names is None:
            use_names = self.use_names

        m = self.mapping.copy()
        m.update(mapping or dict())
        mapping = m

        if bind:
            return self.injector.bind(func=func, mapping=mapping,
                                      use_names=use_names)

        return self.injector.inject(func=func, mapping=mapping,
                                    use_names=use_names)

    def register(self,
                 cls=None,  # type: type
                 singleton=True,  # type: bool
                 auto_wire=None,  # type: Union[bool, Iterable[str]]
                 mapping=None,  # type: Dict
                 use_names=None  # type: Union[bool, Iterable[str]]
                 ):
        # type: (...) -> Callable
        """Register a dependency by its class.

        Args:
            cls (type): Object to register as a dependency.
            singleton (bool, optional): A singleton will be only be
                instantiated once. Otherwise the dependency will instantiated
                anew every time. Defaults to True.
            auto_wire (bool or tuple of strings, optional): Injects
                automatically the dependencies of the methods specified, or
                only of :code:`__init__()` if True. Default to True.
            mapping (dict, optional): Custom mapping of the argument s name
                to their respective dependency id. Overrides annotations.
                Defaults to None.
            use_names (bool, optional): Whether the arguments name
                should be used to search for a dependency when no mapping,
                nor annotation is found. Defaults to False.

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
                    mapping=mapping,
                    use_names=use_names
                )

            self._factories.register(dependency_id=_cls, factory=_cls,
                                     singleton=singleton)

            return _cls

        return cls and register_class(cls) or register_class

    def factory(self,
                func=None,  # type: Callable
                dependency_id=None,  # type: Any
                auto_wire=None,  # type: Union[bool, Iterable[str]]
                singleton=True,  # type: bool
                mapping=None,  # type: Dict
                use_names=None,  # type: Union[bool, Iterable[str]]
                build_subclasses=False  # type: bool
                ):
        # type: (...) -> Callable
        """Register a dependency providers, a factory to build the dependency.

        Args:
            func (callable): Callable which builds the dependency.
            dependency_id (hashable object, optional): Id of the dependency.
                Defaults to the dependency_provider.
            singleton (bool, optional): If True the dependency_provider is
                called only once. Otherwise it is called anew every time.
                Defaults to True.
            auto_wire (bool or tuple of strings, optional): Injects
                automatically the dependencies of the methods specified, or
                only of :code:`__init__()` and :code:`__call__()`
                if True. If True and the providers is a function, its arguments
                will be injected. Defaults to True.
            mapping (dict, optional): Custom mapping of the arguments name
                to their respective dependency id. Overrides annotations.
                Defaults to None.
            use_names (bool, optional): Whether the arguments name
                should be used to search for a dependency when no mapping,
                nor annotation is found. Defaults to False.
            build_subclasses (bool, optional): If True, subclasses will also
                be build with this factory. If multiple factories are defined,
                the first in the MRO is used. Defaults to False.

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
                        mapping=mapping,
                        use_names=use_names
                    )

                factory = factory()
            else:
                if not callable(factory):
                    raise ValueError("factory parameter needs to be callable.")
                type_hints = get_type_hints(factory) or {}

                if auto_wire:
                    factory = self.inject(factory,
                                          mapping=mapping,
                                          use_names=use_names)

            self._factories.register(
                factory=factory,
                singleton=singleton,
                dependency_id=dependency_id or type_hints.get('return'),
                build_subclasses=build_subclasses
            )
            return factory

        return func and register_factory(func) or register_factory

    def wire(self, cls=None, methods=None, **inject_kwargs):
        # type: (type, Iterable[str], **Any) -> Callable
        """Wire a class by injecting the dependencies in all specified methods.

        Args:
            cls (type): class to wire.
            methods (tuple of strings, optional): Name of the methods for which
                dependencies should be injected. Defaults to all defined
                methods.
            **inject_kwargs: Keyword arguments passed on to :py:meth:`inject`.

        Returns:
            type: Wired class.

        """

        def wire_methods(_cls):
            # TODO: use nonlocal once Python 2.7 support drops.
            _methods = methods
            if _methods is None:
                _methods = (
                    name
                    for name, _ in inspect.getmembers(
                        _cls,
                        # Retrieve static methods, class methods, methods.
                        predicate=lambda f: (inspect.isfunction(f)
                                             or inspect.ismethod(f))
                    )
                )

            for method in _methods:
                setattr(_cls,
                        method,
                        self.inject(getattr(_cls, method), **inject_kwargs))

            return _cls

        return cls and wire_methods(cls) or wire_methods

    def attrib(self, dependency_id=None, use_name=None, **attr_kwargs):
        # type: (Any, Union[bool, Iterable[str]], **Any) -> Callable
        """Injects a dependency with attributes defined with attrs package.

        Args:
            dependency_id (hashable object, optional): Id of the dependency to
                inject. Defaults to the annotation or attribute name if
                use_names.
            use_name (bool, optional): If True, use the attribute name to
                identify the dependency. Defaults to False.
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
            try:
                _id = factory._dependency_id
            except AttributeError:
                _id = dependency_id
                if _id is None:
                    cls = instance.__class__
                    type_hints = get_type_hints(cls) or {}

                    for attribute in attr.fields(cls):
                        # Dirty way to find the attrib annotation.
                        # Maybe attr will eventually provide the annotation ?
                        if isinstance(attribute.default, attr.Factory) \
                                and attribute.default.factory is factory:
                            try:
                                _id = type_hints[attribute.name]
                            except KeyError:
                                if use_name:
                                    _id = attribute.name
                                    break
                            else:
                                break
                    else:
                        raise ValueError(
                            "No dependency could be detected. Please specify "
                            "the parameter `dependency_id` or `use_name=True`."
                            "Annotations may also be used."
                        )

                factory._dependency_id = _id

            return self.container[_id]

        return attr.ib(default=attr.Factory(factory, takes_self=True),
                       **attr_kwargs)

    def parameters(self,
                   data,  # type: Union[RawConfigParser, Dict]
                   parser=None,  # type: Union[Callable, str]
                   prefix='',  # type: str
                   sep='.'  # type: str
                   ):
        # type: (...) -> Callable

        def register_parser(f):
            if f == 'split':
                def f(dependency_id):
                    if isinstance(dependency_id, basestring) \
                            and dependency_id.startswith(prefix):
                        return dependency_id[len(prefix):].split(sep)
            elif not callable(f):
                raise ValueError("parser must be callable or be in {'split'}")

            if not PY3 and isinstance(data, RawConfigParser):
                parameters_ = ConfigParserWrapper(data)

                def f_(dependency_id):
                    return [f(dependency_id)]
            else:
                parameters_ = data
                f_ = f

            self._parameters.register(f_, parameters_)

            return f

        return parser and register_parser(parser) or register_parser

    def provider(self,
                 cls=None,  # type: type
                 auto_wire=None,  # type: Union[bool, Iterable[str]]
                 mapping=None,  # type: Dict
                 use_names=None  # type: Union[bool, Iterable[str]]
                 ):
        # type: (...) -> Callable
        """Register a providers by its class.

        Args:
            cls (type): class to register,,,,, as a providers.
            auto_wire (bool or tuple of strings,77 otional): Injects
                automatically the dependencies of 7he methods specified, or
                only of :py:meth:`__init__` if Tru7booloole. Defaults to True.
            mapping (dict, optional): Custom mapping of the argument s name
                bool to their respective dependency id. Overrides annotations.
                Defaults to None.
            use_names (bool, optional): Whether the arguments name
                should be used to search for a dependency when no mapping,
                nor annotation is found. Defaults to False.

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
                    mapping=mapping,
                    use_names=use_names
                )

            instance = _cls()
            instance.__antidote_provide__ = _ignore_arguments_excess(
                instance.__antidote_provide__
            )

            self.container.providers[_cls] = instance

            return _cls

        return cls and register_provider(cls) or register_provider


def _ignore_arguments_excess(func):
    arg_spec, has_var_args, has_var_kwargs = get_arguments_specification(func)

    if has_var_args and has_var_kwargs:
        return func

    @wrapt.decorator
    def decorator(wrapper, _, args, kwargs):
        # Method is supposed to be bound (self is not in the arguments).
        if len(args) == 1 and not len(kwargs):
            return wrapper(*args)

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

        return wrapper(*new_args, **new_kwargs)

    return decorator(func)


class ConfigParserWrapper(object):
    __slots__ = ('config_parser',)

    def __init__(self, config_parser):
        self.config_parser = config_parser

    def __getitem__(self, item):
        try:
            section, option = item
            return self.config_parser.get(section, option)
        except (ValueError, NoSectionError, NoOptionError):
            raise KeyError(item)
