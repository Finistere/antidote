from typing import Any

from .._extension.providers import TagProvider
from .._extension.providers.service import Build, ServiceProvider
from .._internal import API
from .._internal.utils import AbstractMeta
from ..core import inject

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
            **kwargs: Arguments passed on to :code:`__init__()`.

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
    from ...service import Service

    conf = conf or getattr(cls, '__antidote__', None)
    if not isinstance(conf, Service.Conf):
        raise TypeError(f"Service configuration (__antidote__) is expected to be a "
                        f"{Service.Conf}, not a {type(conf)}")

    wiring = conf.wiring

    if wiring is not None:
        wiring.wire(cls)

    service_provider.register(cls, singleton=conf.singleton)

    if conf.tags is not None:
        if tag_provider is None:
            raise RuntimeError("No TagProvider registered, cannot use tags.")
        tag_provider.register(dependency=cls, tags=conf.tags)
