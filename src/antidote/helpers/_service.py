from typing import Any, Callable, cast

from .._internal import API
from .._internal.utils import AbstractMeta, raw_getattr
from ..core import inject
from ..core.utils import Dependency
from ..providers.service import Build, ServiceProvider
from ..providers.tag import TagProvider

_ABSTRACT_FLAG = '__antidote_abstract'


@API.private
class ServiceMeta(AbstractMeta):
    def __new__(mcls, name, bases, namespace, **kwargs):
        cls = super().__new__(mcls, name, bases, namespace, **kwargs)
        if not kwargs.get('abstract'):
            _configure_service(cls)
        return cls

    @API.public
    def with_kwargs(cls, **kwargs) -> Any:
        """
        Creates a new dependency based on the service which will have the keyword
        arguments provided. If the service is a singleton and identical kwargs are used,
        the same instance will be given by Antidote.

        Args:
            **kwargs: Arguments passed on to :code:`__init__()` or if defined the factory.

        Returns:
            Dependency to be retrieved from Antidote.
        """
        return Build(cls, kwargs)


@API.private
@inject
def _configure_service(cls,
                       service_provider: ServiceProvider,
                       tag_provider: TagProvider = None,
                       conf=None):
    from .service import Service

    conf = conf or getattr(cls, '__antidote__', None)
    if not isinstance(conf, Service.Conf):
        raise TypeError(f"Service configuration (__antidote__) is expected to be a "
                        f"{Service.Conf}, not a {type(conf)}")

    wiring = conf.wiring
    factory = conf.factory
    wire_super = wiring.wire_super if wiring is not None else set()

    if isinstance(factory, str) \
            and factory not in cls.__dict__ \
            and factory not in wire_super:
        raise ValueError(f"factory method '{factory}' is implemented in a mother "
                         f"class, so it must be wired with wire_super.")

    # special case for string factory handled later
    if wiring is not None:
        wiring.wire(cls)

    if factory is None:
        service_provider.register(cls, singleton=conf.singleton)
    elif isinstance(factory, Dependency):
        service_provider.register_with_factory(cls,
                                               factory=Dependency(factory.value),
                                               singleton=conf.singleton,
                                               takes_dependency=True)
    else:
        takes_dependency = True
        func: Callable
        if isinstance(factory, str):
            static_factory = raw_getattr(cls, factory,
                                         with_super=factory in wire_super)
            if isinstance(static_factory, classmethod):
                takes_dependency = False
            else:
                raise TypeError(
                    f"Only class methods and static methods are supported "
                    f"as factories, which '{factory}' is not.")

            func = cast(Callable, getattr(cls, factory))
        else:
            assert callable(factory)
            func = factory

        service_provider.register_with_factory(cls,
                                               factory=func,
                                               singleton=conf.singleton,
                                               takes_dependency=takes_dependency)

    if conf.tags is not None:
        if tag_provider is None:
            raise RuntimeError("No TagProvider registered, cannot use tags.")
        tag_provider.register(dependency=cls, tags=conf.tags)
