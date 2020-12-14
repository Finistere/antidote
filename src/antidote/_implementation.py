from typing import cast, Dict, Tuple, Type

from ._internal import API
from ._providers import IndirectProvider
from ._service import ServiceMeta
from .core import inject

_ABSTRACT_FLAG = '__antidote_abstract'


@API.private
class ImplementationMeta(ServiceMeta):
    def __new__(mcs: 'Type[ImplementationMeta]',
                name: str,
                bases: Tuple[type, ...],
                namespace: Dict[str, object],
                **kwargs: object
                ) -> 'ImplementationMeta':
        interface = None
        if any(isinstance(b, ImplementationMeta) for b in bases):
            if kwargs.get("abstract"):
                raise ValueError("Implementation does not support abstract sub classes")

            if len(bases) < 2:
                raise TypeError("The interface to be implemented must be specified "
                                "as first base class.")
            interface, impl_base, *_ = bases

            if not isinstance(impl_base, ImplementationMeta) \
                    or sum(1 for b in bases if isinstance(b, ImplementationMeta)) > 1:
                raise TypeError("The second base class, and only this one, "
                                "must be Implementation.")

        cls = cast(
            ImplementationMeta,
            super().__new__(mcs, name, bases, namespace, **kwargs)
        )

        if interface is not None:
            _configure_implementation(interface, cls)

        return cls


@API.private
@inject
def _configure_implementation(interface: type,
                              cls: ImplementationMeta,
                              indirect_provider: IndirectProvider = None) -> None:
    assert indirect_provider is not None
    indirect_provider.register_static(interface, cls)
