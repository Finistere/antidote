import inspect
from typing import Any, Callable, cast, get_type_hints, Iterable, Tuple, Union

from antidote.core import Lazy
from ..core import DependencyContainer, inject


def prepare_callable(obj: Union[Callable, type],
                     auto_wire: Union[bool, Iterable[str]],
                     use_mro: Union[bool, Iterable[str]],
                     container: DependencyContainer,
                     **inject_kwargs
                     ) -> Tuple[Union[Callable, type], Union[Callable, Lazy], Any]:
    if inspect.isclass(obj):
        obj = cast(type, obj)
        if '__call__' not in dir(obj):
            raise TypeError("A Factory class must implement __call__()")
        from ..helpers import register, wire

        type_hints = get_type_hints(obj.__call__)

        if auto_wire:
            if auto_wire is True:
                methods = ('__init__', '__call__')  # type: Tuple[str, ...]
            else:
                methods = tuple(cast(Iterable[str], auto_wire))

            obj = cast(type, wire(obj,
                                  methods=methods,
                                  use_mro=use_mro,
                                  container=container,
                                  ignore_missing_methods=auto_wire is True,
                                  **inject_kwargs))

        obj = register(obj, auto_wire=False, container=container)
        func = Lazy(obj)  # type: Union[Callable, Lazy]
    elif inspect.isfunction(obj):
        obj = cast(Callable, obj)
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
