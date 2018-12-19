import inspect
from typing import (get_type_hints)

from ..injection.inject import inject
from ..injection.wiring import wire


def prepare_class(cls, auto_wire, **inject_kwargs):
    """
    Used by the helpers to wire a class automatically.
    """
    if not inspect.isclass(cls):
        raise ValueError("Expecting a class, got a {}".format(type(cls)))

    if auto_wire:
        cls = wire(cls,
                   methods=(('__init__',)
                            if auto_wire is True else
                            auto_wire),
                   **inject_kwargs)

    return cls


def prepare_callable(obj, auto_wire, **inject_kwargs):
    """
    Used by the helpers to wire a callable, or a class implementing __call__,
    automatically.
    """
    if inspect.isclass(obj):
        # Only way to accurately test if obj has really a __call__()
        # method.
        if '__call__' not in dir(obj):
            raise ValueError("Factory class needs to be callable.")
        type_hints = get_type_hints(obj.__call__)

        if auto_wire:
            obj = wire(obj,
                       methods=(('__init__', '__call__')
                                if auto_wire is True else
                                auto_wire),
                       **inject_kwargs)

        factory = obj()
    else:
        if not callable(obj):
            raise ValueError("factory parameter needs to be callable.")

        type_hints = get_type_hints(obj)
        obj = factory = inject(obj, **inject_kwargs) if auto_wire else obj

    return obj, factory, (type_hints or {}).get('return')
