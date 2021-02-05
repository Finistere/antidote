from typing import Dict, Tuple, Type, cast

from ._internal import API
from ._internal.utils import AbstractMeta
from ._providers import ServiceProvider
from ._providers.service import Build
from .core import Provide, inject

_ABSTRACT_FLAG = '__antidote_abstract'


@API.private
class ServiceMeta(AbstractMeta):
    def __new__(mcs: 'Type[ServiceMeta]',
                name: str,
                bases: Tuple[type, ...],
                namespace: Dict[str, object],
                **kwargs: object
                ) -> 'ServiceMeta':
        cls = cast(
            ServiceMeta,
            super().__new__(mcs, name, bases, namespace, **kwargs)  # type: ignore
        )
        if not kwargs.get('abstract'):
            _configure_service(cls)
        return cls

    @API.public
    def _with_kwargs(cls, **kwargs: object) -> object:
        """
        Creates a new dependency based on the service with the given arguments. The new
        dependency will have the same scope as the original one.

        The recommended usage is to provide a classmethod exposing only parameters that
        may be changed:

        .. doctest:: service_meta

            >>> from antidote import Service, world
            >>> class Database(Service):
            ...     def __init__(self, host: str = 'localhost'):
            ...         self.host = host
            ...
            ...     @classmethod
            ...     def with_host(cls, host: str) -> object:
            ...         return cls._with_kwargs(host=host)
            >>> db = world.get(Database.with_host(host='remote'))
            >>> db.host
            'remote'
            >>> # As Database is defined as a singleton, the same is applied:
            ... world.get(Database.with_host(host='remote')) is db
            True
            >>> # Custom dependencies will NEVER be equal to the default one
            ... world.get(Database) is db
            False

        Args:
            **kwargs: Arguments passed on to :code:`__init__()`.

        Returns:
            Dependency to be retrieved from Antidote. You cannot use it directly.
        """
        return Build(cls, kwargs)


@API.private
@inject
def _configure_service(cls: type,
                       service_provider: Provide[ServiceProvider] = None,
                       conf: object = None) -> None:
    from .service import Service
    assert service_provider is not None

    conf = conf or getattr(cls, '__antidote__', None)
    if not isinstance(conf, Service.Conf):
        raise TypeError(f"Service configuration (__antidote__) is expected to be a "
                        f"{Service.Conf}, not a {type(conf)}")

    wiring = conf.wiring

    if wiring is not None:
        wiring.wire(cls)

    service_provider.register(cls, scope=conf.scope)
