from __future__ import annotations

import builtins
import inspect
from typing import Any, cast, Optional, Tuple

from typing_extensions import Annotated, get_args, get_origin

from ._injection import ArgDependency
from .annotations import (AntidoteAnnotation, From, FromArg, Get, INJECT_SENTINEL)
from .injection import Arg
from .marker import InjectMeMarker, Marker
from .._internal import API
from .._internal.argspec import Argument


@API.private
def extract_annotated_dependency(type_hint: object) -> object:
    origin = get_origin(type_hint)

    # Dependency explicitly given through Annotated (PEP-593)
    if origin is Annotated:
        args = get_args(type_hint)
        antidote_annotations = [a
                                for a in getattr(type_hint, "__metadata__", tuple())
                                if isinstance(a, AntidoteAnnotation)]
        if len(antidote_annotations) > 1:
            raise TypeError(f"Multiple AntidoteAnnotation are not supported. "
                            f"Found {antidote_annotations}")
        elif antidote_annotations:
            annotation: AntidoteAnnotation = antidote_annotations[0]
            if annotation is INJECT_SENTINEL:
                return args[0]
            elif isinstance(annotation, Get):
                return annotation.dependency
            elif isinstance(annotation, From):
                return args[0] @ annotation.source
            else:
                raise TypeError(f"Annotation {annotation} cannot be used"
                                f"outside of a function.")
        else:
            return args[0]

    return type_hint


_BUILTINS_TYPES = {e for e in builtins.__dict__.values() if isinstance(e, type)}


@API.private
def extract_annotated_arg_dependency(argument: Argument) -> object:
    type_hint, origin, args = _extract_type_hint(argument)

    # Dependency explicitly given through Annotated (PEP-593)
    if origin is Annotated:
        antidote_annotations = [a
                                for a in type_hint.__metadata__
                                if isinstance(a, AntidoteAnnotation)]
        if len(antidote_annotations) > 1:
            raise TypeError(f"Multiple AntidoteAnnotation are not supported. "
                            f"Found {antidote_annotations}")
        elif antidote_annotations:
            if isinstance(argument.default, Marker):
                raise TypeError("Cannot use a Marker with an Antidote annotation.")

            # If antidote annotation, no additional check is done we just return
            # what was specified.
            annotation: AntidoteAnnotation = antidote_annotations[0]
            if annotation is INJECT_SENTINEL:
                return args[0]
            elif isinstance(annotation, Get):
                return annotation.dependency
            elif isinstance(annotation, From):
                return args[0] @ annotation.source
            elif isinstance(annotation, FromArg):
                arg = Arg(argument.name,
                          argument.type_hint,
                          argument.type_hint_with_extras)
                return annotation.function(arg)  # type: ignore
            else:
                raise TypeError(f"Unsupported AntidoteAnnotation, {type(annotation)}")

    if isinstance(argument.default, Marker):
        from .._constants import LazyConst

        marker = argument.default
        dependency: object
        if isinstance(marker, Get):
            dependency = marker.dependency
        elif isinstance(marker, LazyConst):
            dependency = cast(object, marker)
        elif isinstance(marker, InjectMeMarker):
            if not is_valid_class_type_hint(type_hint):
                raise TypeError(
                    f"Cannot use marker @inject.me with non class type hint: {type_hint}")
            if marker.source is not None:
                dependency = Get(type_hint, source=marker.source).dependency
            else:
                dependency = type_hint
        else:
            raise TypeError("Custom Marker are NOT supported.")

        return ArgDependency(dependency, optional=argument.is_optional)

    return None


@API.private
def extract_auto_provided_arg_dependency(argument: Argument) -> Optional[type]:
    type_hint, origin, args = _extract_type_hint(argument)
    dependency = type_hint

    if origin is Annotated:
        antidote_annotations = [a
                                for a in type_hint.__metadata__
                                if isinstance(a, AntidoteAnnotation)]
        if not antidote_annotations:
            dependency = args[0]

    if is_valid_class_type_hint(dependency):
        return cast(type, dependency)

    return None


@API.private
def is_valid_class_type_hint(type_hint: object) -> bool:
    return (getattr(type_hint, '__module__', '') != 'typing'
            and type_hint not in _BUILTINS_TYPES
            and (isinstance(type_hint, type) and inspect.isclass(type_hint)))


@API.private
def _extract_type_hint(argument: Argument) -> Tuple[Any, object, Tuple[object, ...]]:
    type_hint = argument.type_hint_with_extras
    origin = get_origin(type_hint)
    args = get_args(type_hint)

    # Optional
    if argument.is_optional:
        type_hint = args[0] if isinstance(None, args[1]) else args[0]
        origin = get_origin(type_hint)
        args = get_args(type_hint)

    return type_hint, origin, args
