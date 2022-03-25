from __future__ import annotations

import inspect
import sys
from typing import Any, Callable, cast, Dict, Iterator, List, Sequence, Set, Union

from typing_extensions import get_args, get_origin, get_type_hints

from .utils import FinalImmutable

if sys.version_info >= (3, 10):
    from types import UnionType
else:
    UnionType = Union


class Argument(FinalImmutable):
    __slots__ = ('name', 'default', 'type_hint', 'type_hint_with_extras')
    name: str
    default: object
    type_hint: Any
    type_hint_with_extras: Any

    @property
    def has_default(self) -> bool:
        return self.default is not inspect.Parameter.empty

    @property
    def is_optional(self) -> bool:
        origin = get_origin(self.type_hint)
        if origin is Union or origin is UnionType:
            args = cast(Any, get_args(self.type_hint))
            return len(args) == 2 and (isinstance(None, args[1]) or isinstance(None, args[0]))
        return False

    def __repr__(self) -> str:
        if self.type_hint is self.type_hint_with_extras:
            return f"Argument({self})"
        return f"Argument({self}, extras={self.type_hint_with_extras})"

    def __str__(self) -> str:
        type_hint = getattr(self.type_hint, "__name__", repr(self.type_hint))
        common = f'{self.name}:{type_hint}'
        return common + f" = {self.default}" if self.has_default else common


class Arguments:
    """ Used when generating the injection wrapper """
    arguments: Sequence[Argument]
    has_var_positional: bool
    has_var_keyword: bool
    has_self: bool
    without_self: Arguments
    __name_to_argument: Dict[str, Argument]

    @classmethod
    def from_callable(cls,
                      func: Union[Callable[..., object], staticmethod[Any], classmethod[Any]],
                      *,
                      ignore_type_hints: bool = False
                      ) -> Arguments:
        if not (callable(func) or isinstance(func, (staticmethod, classmethod))):
            raise TypeError(f"func must be a callable or a static/class-method. "
                            f"Not a {type(func)}")
        return cls._build(
            func=func.__func__ if isinstance(func, (staticmethod, classmethod)) else func,
            unbound_method=is_unbound_method(func),  # doing it before un-wrapping.
            ignore_type_hints=ignore_type_hints
        )

    @classmethod
    def _build(cls,
               *,
               func: Callable[..., object],
               unbound_method: bool,
               ignore_type_hints: bool
               ) -> Arguments:
        arguments: List[Argument] = []
        has_var_positional = False
        has_var_keyword = False

        # typing is used, as lazy evaluation is not done properly with Signature.
        if ignore_type_hints:
            type_hints = {}
            extra_type_hints = {}
        else:
            type_hints = get_type_hints(func)
            extra_type_hints = get_type_hints(func, include_extras=True)

        for name, parameter in inspect.signature(func).parameters.items():
            if parameter.kind is parameter.VAR_POSITIONAL:
                has_var_positional = True
            elif parameter.kind is parameter.VAR_KEYWORD:
                has_var_keyword = True
            else:
                arguments.append(Argument(
                    name=name,
                    default=parameter.default,
                    type_hint=type_hints.get(name),
                    type_hint_with_extras=extra_type_hints.get(name)
                ))

        return Arguments(arguments=tuple(arguments),
                         has_var_positional=has_var_positional,
                         has_var_keyword=has_var_keyword,
                         has_self=unbound_method)

    def __init__(self,
                 arguments: Sequence[Argument],
                 has_var_positional: bool,
                 has_var_keyword: bool,
                 has_self: bool):
        self.arguments = arguments
        self.__name_to_argument = dict(((arg.name, arg)
                                        for arg in arguments))
        self.has_var_positional = has_var_positional
        self.has_var_keyword = has_var_keyword
        self.has_self = has_self

        if has_self:
            self.without_self = Arguments(self.arguments[1:], self.has_var_positional,
                                          self.has_var_keyword, has_self=False)
        else:
            self.without_self = self

    @property
    def arg_names(self) -> Set[str]:
        return set(self.__name_to_argument.keys())

    def __repr__(self) -> str:
        args = [str(arg) for arg in self.__name_to_argument.values()]
        if self.has_var_positional:
            args.append("*args")
        if self.has_var_keyword:
            args.append("**kwargs")

        return f"Arguments({', '.join(args)})"

    def __getitem__(self, index: Union[str, int]) -> Argument:
        if isinstance(index, str):
            return self.__name_to_argument[index]
        elif isinstance(index, int):
            return self.arguments[index]
        else:
            raise TypeError(f"Unsupported index {index!r}")

    def __contains__(self, name: str) -> bool:
        return name in self.__name_to_argument

    def __len__(self) -> int:
        return len(self.arguments)

    def __iter__(self) -> Iterator[Argument]:
        return iter(self.arguments)


def is_unbound_method(func: Union[Callable[..., object], staticmethod[Any], classmethod[Any]]
                      ) -> bool:
    """
    Methods and nested function will have a different __qualname__ than
    __name__ (See PEP-3155).

    >>> class A:
    ...     def f(self):
    ...         pass
    >>> A.f.__qualname__
    'A.f'

    This helps us differentiate method defined in a module and those for a class.
    """
    if isinstance(func, staticmethod):
        return False

    if isinstance(func, classmethod):
        func = func.__func__

    return (func.__qualname__ != func.__name__  # not top level
            # not a bound method (self/cls already bound)
            and not inspect.ismethod(func)
            # not nested function
            and not func.__qualname__[:-len(func.__name__)].endswith("<locals>."))
