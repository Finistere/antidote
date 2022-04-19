from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterator, List, Mapping, Optional, Sequence, Set, Union

from typing_extensions import final, get_type_hints

from .utils import is_optional


@final
@dataclass(frozen=True)
class Argument:
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
        return is_optional(self.type_hint)

    def __repr__(self) -> str:
        if self.type_hint is self.type_hint_with_extras:
            return f"Argument({self})"
        return f"Argument({self}, extras={self.type_hint_with_extras})"

    def __str__(self) -> str:
        type_hint = getattr(self.type_hint, "__name__", repr(self.type_hint))
        common = f'{self.name}:{type_hint}'
        return common + f" = {self.default}" if self.has_default else common


@final
@dataclass(frozen=True, init=False)
class Arguments:
    """ Used when generating the injection wrapper """
    __slots__ = ('arguments', 'has_var_positional', 'has_var_keyword', 'has_self', 'without_self',
                 '_name_to_argument')
    arguments: Sequence[Argument]
    has_var_positional: bool
    has_var_keyword: bool
    has_self: bool
    without_self: Arguments
    _name_to_argument: Dict[str, Argument]

    @classmethod
    def from_callable(cls,
                      func: Union[Callable[..., object], staticmethod[Any], classmethod[Any]],
                      *,
                      ignore_type_hints: bool = False,
                      type_hints_locals: Optional[Mapping[str, object]] = None
                      ) -> Arguments:
        if not (callable(func) or isinstance(func, (staticmethod, classmethod))):
            raise TypeError(f"func must be a callable or a static/class-method. "
                            f"Not a {type(func)}")
        return cls._build(
            func=func.__func__ if isinstance(func, (staticmethod, classmethod)) else func,
            unbound_method=is_unbound_method(func),  # doing it before un-wrapping.
            ignore_type_hints=ignore_type_hints,
            type_hints_locals=type_hints_locals
        )

    @classmethod
    def _build(cls,
               *,
               func: Callable[..., object],
               unbound_method: bool,
               ignore_type_hints: bool,
               type_hints_locals: Optional[Mapping[str, object]]
               ) -> Arguments:
        arguments: List[Argument] = []
        has_var_positional = False
        has_var_keyword = False

        # typing is used, as lazy evaluation is not done properly with Signature.
        if ignore_type_hints:
            type_hints = {}
            extra_type_hints = {}
        else:
            localns = dict(type_hints_locals) if type_hints_locals is not None else None
            type_hints = get_type_hints(func, localns=localns)
            extra_type_hints = get_type_hints(func, localns=localns, include_extras=True)

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
        object.__setattr__(self, 'arguments', arguments)
        object.__setattr__(self, 'has_var_positional', has_var_positional)
        object.__setattr__(self, 'has_var_keyword', has_var_keyword)
        object.__setattr__(self, 'has_self', has_self)
        object.__setattr__(self, '_name_to_argument', {arg.name: arg for arg in arguments})

        if has_self:
            without_self = Arguments(self.arguments[1:],
                                     self.has_var_positional,
                                     self.has_var_keyword,
                                     has_self=False)
        else:
            without_self = self
        object.__setattr__(self, 'without_self', without_self)

    @property
    def arg_names(self) -> Set[str]:
        return set(self._name_to_argument.keys())

    def __repr__(self) -> str:
        args = [str(arg) for arg in self._name_to_argument.values()]
        if self.has_var_positional:
            args.append("*args")
        if self.has_var_keyword:
            args.append("**kwargs")

        return f"Arguments({', '.join(args)})"

    def __getitem__(self, index: Union[str, int]) -> Argument:
        if isinstance(index, str):
            return self._name_to_argument[index]
        elif isinstance(index, int):
            return self.arguments[index]
        else:
            raise TypeError(f"Unsupported index {index!r}")

    def __contains__(self, name: str) -> bool:
        return name in self._name_to_argument

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
