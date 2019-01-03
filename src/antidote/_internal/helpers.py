import inspect
from typing import Any, Callable, get_type_hints, Iterable, Tuple, TypeVar, Union

from ..core import DependencyContainer, inject
from antidote.core import Lazy

T = TypeVar('T', bound=Union[Callable, type])


def prepare_callable(obj: T,
                     auto_wire: Union[bool, Iterable[str]],
                     use_mro: Union[bool, Iterable[str]],
                     container: DependencyContainer,
                     **inject_kwargs
                     ) -> Tuple[T, Callable, Any]:
    if inspect.isclass(obj):
        if '__call__' not in dir(obj):
            raise TypeError("A Factory class must implement __call__()")
        from ..helpers import register, wire

        type_hints = get_type_hints(obj.__call__)

        if auto_wire:
            obj = wire(obj,
                       methods=(('__init__', '__call__')
                                if auto_wire is True else
                                auto_wire),
                       use_mro=use_mro,
                       container=container,
                       ignore_missing_methods=auto_wire is True,
                       **inject_kwargs)

        obj = register(obj, auto_wire=False, container=container)
        func = Lazy(obj)
    elif inspect.isfunction(obj):
        type_hints = get_type_hints(obj)
        if auto_wire:
            obj = inject(obj,
                         container=container,
                         **inject_kwargs)

        func = obj
    else:
        raise TypeError("Factory must be either a function "
                        "or a class implementing __call__().")

    return obj, func, type_hints.get('return')
