from __future__ import annotations

import warnings
from abc import ABCMeta
from typing import Any, cast, Dict, Tuple, Type

from ._internal import API
from ._internal.utils import AbstractMeta
from ._providers import ServiceProvider
from ._providers.service import Parameterized
from ._utils import validate_method_parameters
from .core import inject

_ABSTRACT_FLAG = '__antidote_abstract'


@API.private
class ServiceMeta(AbstractMeta):
    def __new__(mcs: Type[ServiceMeta],
                name: str,
                bases: Tuple[type, ...],
                namespace: Dict[str, object],
                **kwargs: Any
                ) -> ServiceMeta:
        cls = cast(
            ServiceMeta,
            super().__new__(mcs, name, bases, namespace, **kwargs)
        )
        if not kwargs.get('abstract'):
            _configure_service(cls)
        return cls

    @API.deprecated
    def parameterized(cls, **kwargs: object) -> object:
        """
        .. deprecated:: 1.1
            :code:`parameterized()` is a complex behavior with poor type-safety. Use-cases that
            really benefit from this behavior are few and would be better implemeneted explicitly
            in your own code.

        Creates a new dependency based on the service with the given arguments. The new
        dependency will have the same scope as the original one.

        The recommended usage is to provide a classmethod exposing only parameters that
        may be changed:

        .. doctest:: service_meta

            >>> from antidote import Service, world
            >>> class Database(Service):
            ...     __antidote__ = Service.Conf(parameters=['host'])
            ...
            ...     def __init__(self, host: str):
            ...         self.host = host
            ...
            ...     @classmethod
            ...     def with_host(cls, host: str) -> object:
            ...         return cls.parameterized(host=host)
            >>> db = world.get(Database.with_host(host='remote'))
            >>> db.host
            'remote'
            >>> # As Database is defined as a singleton, the same is applied:
            ... world.get(Database.with_host(host='remote')) is db
            True

        Args:
            **kwargs: Arguments passed on to :code:`__init__()`.

        Returns:
            Dependency to be retrieved from Antidote. You cannot use it directly.
        """
        warnings.warn("Deprecated, parameterized() is too complex and not type-safe",
                      DeprecationWarning)

        from .service import Service
        # Guaranteed through _configure_service()
        conf = cast(Service.Conf, getattr(cls, '__antidote__'))
        if conf.parameters is None:
            raise RuntimeError(f"Service {cls} does not accept any parameters. You must "
                               f"specify them explicitly in the configuration with: "
                               f"Service.Conf(parameters=...))")

        if set(kwargs.keys()) != set(conf.parameters or []):
            raise ValueError(f"Given parameters do not match expected ones. "
                             f"Got: ({','.join(map(repr, kwargs.keys()))}) "
                             f"Expected: ({','.join(map(repr, conf.parameters))})")

        return Parameterized(cls, kwargs)


@API.private
class ABCServiceMeta(ServiceMeta, ABCMeta):
    pass


@API.private
@inject
def _configure_service(cls: type,
                       service_provider: ServiceProvider = inject.me(),
                       conf: object = None) -> None:
    from .service import Service

    conf = conf or getattr(cls, '__antidote__', None)
    if not isinstance(conf, Service.Conf):
        raise TypeError(f"Service configuration (__antidote__) is expected to be a "
                        f"{Service.Conf}, not a {type(conf)}")

    wiring = conf.wiring

    if wiring is not None:
        wiring.wire(cls)

    validate_method_parameters(cls.__init__, conf.parameters)

    service_provider.register(cls, scope=conf.scope)
