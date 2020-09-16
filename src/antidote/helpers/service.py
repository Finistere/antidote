import collections.abc as c_abc
from typing import Callable, final, Iterable, Optional, overload, Tuple, TypeVar, Union

from ._service import ServiceMeta
from .._internal import API
from .._internal.utils import Copy, FinalImmutable
from ..core import Dependency
from ..core.exceptions import DuplicateDependencyError
from ..core.injection import DEPENDENCIES_TYPE
from ..core.wiring import AutoWire, Wiring, WithWiringMixin
from ..providers.tag import Tag

C = TypeVar('C', bound=type)


@API.public
class Service(metaclass=ServiceMeta, abstract=True):
    """
    Abstract base class for a service. It can be retrieved from Antidote simply with its
    class. It will only be instantiated when necessary. By default a service will be
    a singleton and :py:meth:`.__init__` will be wired (injected).

    .. doctest:: register_service

        >>> from antidote import Service, world
        >>> class MyService(Service):
        ...     pass
        >>> world.get[MyService]()
        MyService

    For customization use :py:attr:`.__antidote__`:

    .. doctest:: register_service

        >>> class MyService(Service):
        ...     __antidote__ = Service.Conf(singleton=False) \\
        ...         .with_wiring(use_names=True)

    One can customize the instantiation and use the same service with different
    configuration:

    .. doctest:: register_service

        >>> class MyService(Service):
        ...     def __init__(self, name = 'default'):
        ...         self.name = name
        >>> world.get[Service]().name
        default
        >>> s = world.get[Service](Service.with_kwargs(name='perfection'))
        >>> s.name
        perfection
        >>> # The same instance will be returned for those keywords as MyService is
        ... # defined as a singleton.
        ... s is world.get(Service.with_kwargs(name='perfection'))
        True
        >>> from antidote import inject
        ... # You can also keep the dependency and re-use it
        ... PerfectionService = Service.with_kwargs(name='perfection')
        ... @inject(dependencies=dict(service=PerfectionService))
        ... def f(service):
        ...     return service
        >>> f() is s
        True

    """

    @final
    class Conf(FinalImmutable, WithWiringMixin):
        """
        Immutable service configuration. To change parameters on a existing instance, use
        either method :py:meth:`.copy` or
        :py:meth:`.core.wiring.WithWiringMixin.with_wiring`.
        """
        __slots__ = ('wiring', 'singleton', 'tags', 'factory')
        wiring: Optional[Wiring]
        singleton: bool
        tags: Optional[Tuple[Tag]]
        factory: Optional[Union[str, Callable, Dependency]]

        def __init__(self,
                     *,
                     wiring: Optional[Union[Wiring, AutoWire]] = AutoWire.auto,
                     singleton: bool = True,
                     tags: Optional[Iterable[Tag]] = None,
                     factory: Optional[Union[str, Callable, Dependency]] = None):
            """
            Args:
                wiring: Wiring to be applied on the service. By default only
                    :code:`__init__()` will be wired. Unless :py:attr:`.factory` is class
                    method name, in which case only the latter would be wired. To
                    deactivate any wiring at all use :py:obj:`None`.
                singleton: Whether the service is a singleton or not. A singleton is
                    instantiated only once. Defaults to :py:obj:`True`
                tags: Iterable of :py:class:`~..providers.tag.Tag` tagging to the service.
                factory: Factory to be used to construct the service. Defaults to
                    :py:obj:`None`.  Can be one of:

                    - String: Name of a class method to be used. Unless overridden in
                      :py:attr:`.wiring`, it will be auto-wired and can be defined in a
                      parent class.
                    - Callable: The class will be given as first argument.
                    - :py:class:`~.core.utils.Dependency`: The dependency will be
                      retrieved only at instantiation and used to create the service. The
                      class will be given as first argument.
            """
            if not isinstance(singleton, bool):
                raise TypeError(f"singleton can be a boolean, "
                                f"but not a {type(singleton)}")
            if not (tags is None or isinstance(tags, c_abc.Iterable)):
                raise TypeError(f"tags can be None or an iterable of strings/Tags, "
                                f"but not a {type(tags)}")
            elif tags is not None:
                tags = tuple(tags)
                if not all(isinstance(t, Tag) for t in tags):
                    raise TypeError(f"Not all tags were instances of Tag: {tags}")
            if not (factory is None
                    or callable(factory)
                    or isinstance(factory, (str, Dependency))):
                raise TypeError(f"factory can be None, a callable, a method name "
                                f"or dependency, but not a {type(factory)}")
            if wiring is AutoWire.auto:
                if isinstance(factory, str):
                    wiring = Wiring(methods=(factory,))
                else:
                    wiring = Wiring(methods=['__init__'],
                                    ignore_missing_method=['__init__'])
            elif not (wiring is None or isinstance(wiring, Wiring)):
                raise TypeError(f"wiring can be None or a Wiring, "
                                f"but not a {type(wiring)}")
            super().__init__(wiring=wiring, singleton=singleton, tags=tags,
                             factory=factory)

        def copy(self,
                 *,
                 wiring: Union[Optional[Wiring], Copy] = Copy.IDENTICAL,
                 singleton: Union[bool, Copy] = Copy.IDENTICAL,
                 tags: Union[Optional[Iterable[Tag]], Copy] = Copy.IDENTICAL,
                 factory: Union[
                     Optional[Union[str, Callable, Dependency]], Copy] = Copy.IDENTICAL):
            """
            Copies current configuration and overrides only specified arguments.
            Accepts the same arguments as :py:meth:`.__init__`
            """
            return Service.Conf(
                wiring=self.wiring if wiring is Copy.IDENTICAL else wiring,
                singleton=self.singleton if singleton is Copy.IDENTICAL else singleton,
                tags=self.tags if tags is Copy.IDENTICAL else tags,
                factory=self.factory if factory is Copy.IDENTICAL else factory,
            )

    __antidote__: Conf = Conf()
    """
    Configuration of the service. Defaults to wire :py:meth:`.__init__`.
    """


@overload
def register(klass: C,  # noqa: E704  # pragma: no cover
             *,
             singleton: bool = True,
             factory: Union[str, Callable, Dependency] = None,
             auto_wire: Union[bool, Iterable[str]] = None,
             dependencies: DEPENDENCIES_TYPE = None,
             use_names: Union[bool, Iterable[str]] = None,
             use_type_hints: Union[bool, Iterable[str]] = None,
             wire_super: Union[bool, Iterable[str]] = None,
             tags: Iterable[Tag] = None
             ) -> C: ...


@overload
def register(*,  # noqa: E704  # pragma: no cover
             singleton: bool = True,
             factory: Union[str, Callable, Dependency] = None,
             auto_wire: Union[bool, Iterable[str]] = None,
             dependencies: DEPENDENCIES_TYPE = None,
             use_names: Union[bool, Iterable[str]] = None,
             use_type_hints: Union[bool, Iterable[str]] = None,
             wire_super: Union[bool, Iterable[str]] = None,
             tags: Iterable[Tag] = None
             ) -> Callable[[C], C]: ...


@API.public
def register(klass=None,
             *,
             singleton: bool = True,
             factory: Union[str, Callable, Dependency] = None,
             auto_wire: Union[bool, Iterable[str]] = None,
             dependencies: DEPENDENCIES_TYPE = None,
             use_names: Union[bool, Iterable[str]] = None,
             use_type_hints: Union[bool, Iterable[str]] = None,
             wire_super: Union[bool, Iterable[str]] = None,
             tags: Iterable[Tag] = None):
    """
    Register a service: the class itself is the dependency. Prefer using
    :py:class:`.Service` when possible, it provides more features such as
    :py:meth:`.Service.with_kwargs`. This decorator is intended for registration of
    class which cannot inherit :py:class:`.Service`. By default :code:`__init__()` will
    be auto-wired. If you do no wish to change anything on the class use the following:

    .. doctest::

        >>> from antidote import register
        >>> @register(auto_wire=False)
        ... class MyComplexService:
        ...     pass

    .. note::

        If your wish to declare to register an external class to Antidote, consider using
        a factory with either :py:class:`~.helpers.factory.Factory` or
        :py:func:`~.helpers.factory.factory`

    Args:
        klass: Class to register as a dependency. It will be instantiated  only when
            requested.
        singleton: If True, the service will be a singleton and instantiated only once.
        factory: Factory to be used to construct the service. Defaults to :py:obj:`None`.
            Can be one of:
            
            - String: Name of a class method to be used. Unless overridden in 
              :code:`auto_wire`, it will be auto-wired and can be defined in a parent
              class.
            - Callable: The class will be given as first argument.
            - :py:class:`~.core.utils.Dependency`: The dependency will be retrieved only 
              at instantiation and used to create the service. The class will be given as
              first argument.
        auto_wire: Whether the class should auto-wired. Defaults to :py:obj:`True`, which
            will auto-wire :code:`__init__()` or :code:`factory` if it's a class method
            name. A list of methods names can be provided which will be propagated to
            :py:class:`.core.wiring.Wiring`.
        dependencies: Propagated for every auto-wired method to
            :py:func:`~.injection.inject`.
        use_names: Propagated for every auto-wired method to
            :py:func:`~.injection.inject`.
        use_type_hints: Propagated for every auto-wired method to
            :py:func:`~.injection.inject`.
        wire_super: Propagated to :py:class:`.core.wiring.Wiring`. If :code:`factory` is
            a class method name, it will be automatically added unless overridden.
        tags: Iterable of :py:class:`~..providers.tag.Tag` applied to the service.

    Returns:
        The class or the class decorator.

    """
    auto_wire = auto_wire if auto_wire is not None else True

    if not isinstance(auto_wire, (bool, c_abc.Iterable)) or isinstance(auto_wire, str):
        raise TypeError(f"auto_wire must be a boolean or an iterable of method names, "
                        f"not {type(auto_wire)}")
    if isinstance(auto_wire, c_abc.Iterable):
        auto_wire = set(auto_wire)
        if not all(isinstance(m, str) for m in auto_wire):
            raise TypeError(f"auto_wire can only consists of method names (str), "
                            f"not {auto_wire}")

    def reg(cls):
        from ._service import _configure_service
        nonlocal wire_super

        if issubclass(cls, Service):
            raise DuplicateDependencyError(f"{cls} is already defined as a dependency "
                                           f"by inheriting {Service}")

        if auto_wire:
            if auto_wire is True:
                if isinstance(factory, str):
                    ignore_missing_method = False
                    methods = (factory,)
                    if wire_super is None:
                        wire_super = (factory,)
                else:
                    methods = ['__init__']
                    ignore_missing_method = methods
            else:
                ignore_missing_method = auto_wire
                methods = auto_wire
            wiring = Wiring(methods=methods,
                            dependencies=dependencies,
                            use_names=use_names,
                            use_type_hints=use_type_hints,
                            wire_super=wire_super,
                            ignore_missing_method=ignore_missing_method)
        else:
            wiring = None

        _configure_service(cls,
                           conf=Service.Conf(wiring=wiring,
                                             singleton=singleton,
                                             factory=factory,
                                             tags=tags))

        return cls

    return klass and reg(klass) or reg
