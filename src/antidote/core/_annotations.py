from __future__ import annotations

import builtins
from typing import Any, cast, Optional, Tuple

from typing_extensions import Annotated, get_args, get_origin

from .annotations import AntidoteAnnotation, From, FromArg, Get, INJECT_SENTINEL
from .container import RawMarker
from .marker import InjectClassMarker, InjectFromSourceMarker, InjectImplMarker, Marker
from .typing import Dependency
from .._internal import API
from .._internal.argspec import Argument
from .._internal.utils import Default


@API.private
@API.deprecated
def extract_annotated_dependency(type_hint: object) -> object:
    origin = get_origin(type_hint)

    # Dependency explicitly given through Annotated (PEP-593)
    if origin is Annotated:
        args = get_args(type_hint)
        antidote_annotations = [a
                                for a in getattr(type_hint,
                                                 "__metadata__",
                                                 cast(Tuple[object, ...], tuple()))
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
                from .injection import Arg
                arg = Arg(argument.name,
                          argument.type_hint,
                          argument.type_hint_with_extras)
                return annotation.function(arg)  # type: ignore
            else:
                raise TypeError(f"Unsupported AntidoteAnnotation, {type(annotation)}")

    if isinstance(argument.default, RawMarker):
        from ._injection import ArgDependency

        type_hint, origin, args = _extract_type_hint(argument, extras=False)
        marker = argument.default
        dependency: object
        if isinstance(marker, Get):
            return ArgDependency(marker.dependency, default=marker.default)
        elif isinstance(marker, Dependency):
            return ArgDependency(cast(Dependency[object], marker))
        elif isinstance(marker, (InjectClassMarker, InjectImplMarker, InjectFromSourceMarker)):
            if isinstance(marker, InjectFromSourceMarker):
                if not is_valid_class_type_hint(type_hint):
                    raise TypeError(f"@inject.me could not determine class from: {type_hint!r}")
                dependency = Get(type_hint, source=marker.source).dependency
            else:
                from ..lib.interface import ImplementationsOf
                from collections.abc import Sequence, Iterable

                if origin in {Sequence, Iterable, list}:
                    klass = args[0]
                    method = 'all'
                else:
                    klass = type_hint
                    method = 'single'

                # Support generic interfaces
                klass = get_origin(klass) or klass
                if not is_valid_class_type_hint(klass):
                    raise TypeError(f"@inject.me could not determine class from: {klass!r}")
                if isinstance(marker, InjectImplMarker):
                    dependency = getattr(ImplementationsOf[type](klass), method)(
                        *marker.constraints_args,
                        **marker.constraints_kwargs
                    )
                elif method == 'single':
                    dependency = klass
                else:
                    dependency = getattr(ImplementationsOf[type](klass), method)()

            return ArgDependency(dependency,
                                 default=None if argument.is_optional else Default.sentinel)
        else:
            # FIXME: it's ugly, need to rework marker/dependency
            from ..lib.lazy._provider import Lazy
            if isinstance(marker, Lazy):
                return ArgDependency(marker)
            else:
                raise TypeError("Custom Marker are NOT supported.")

    return None


@API.private
@API.deprecated
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
            and isinstance(type_hint, type))


@API.private
def _extract_type_hint(argument: Argument,
                       extras: bool = True
                       ) -> Tuple[Any, Any, Tuple[Any, ...]]:
    type_hint = argument.type_hint_with_extras if extras else argument.type_hint
    origin = get_origin(type_hint)
    args = get_args(type_hint)

    # Optional
    if argument.is_optional:
        type_hint = args[0] if isinstance(None, args[1]) else args[0]
        origin = get_origin(type_hint)
        args = get_args(type_hint)

    return type_hint, origin, args
