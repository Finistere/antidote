import inspect
from typing import (Callable, Iterable, Mapping, Sequence, Union)

from .inject import inject
from ..container import DependencyContainer


def wire(class_: type = None,
         methods: Iterable[str] = None,
         arg_map: Union[Mapping, Sequence] = None,
         use_names: Union[bool, Iterable[str]] = None,
         use_type_hints: Union[bool, Iterable[str]] = None,
         container: DependencyContainer = None
         ) -> Union[Callable, type]:
    """Wire a class by injecting the dependencies in all specified methods.

    Args:
        class_: class to wire.
        methods: Name of the methods for which dependencies should be
            injected. Defaults to all defined methods.
        arg_map: Custom mapping of the arguments name to their respective
            dependency id. A sequence of dependencies can also be
            specified, which will be mapped to the arguments through their
            order. Annotations are overridden.
        use_names: Whether the arguments name should be used to find for
            a dependency. An iterable of names may also be provided to
            restrict this to a subset of the arguments. Annotations are
            overridden, but not the arg_map.
        use_type_hints: Whether the type hints should be used to find for
            a dependency. An iterable of names may also be provided to
            restrict this to a subset of the arguments.

    Returns:
        type: Wired class.

    """

    def wire_methods(cls):
        if not inspect.isclass(cls):
            raise ValueError("Expecting a class, got a {}".format(type(cls)))

        nonlocal methods

        if methods is None:
            methods = map(
                lambda m: m[0],  # get only the name
                inspect.getmembers(
                    cls,
                    # Retrieve static methods, class methods, methods.
                    predicate=lambda f: (inspect.isfunction(f)
                                         or inspect.ismethod(f))
                )
            )

        for method in methods:
            setattr(cls,
                    method,
                    inject(getattr(cls, method),
                           arg_map=arg_map,
                           use_names=use_names,
                           use_type_hints=use_type_hints,
                           container=container))

        return cls

    return class_ and wire_methods(class_) or wire_methods
