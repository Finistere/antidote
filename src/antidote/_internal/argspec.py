import inspect
from typing import Callable, get_type_hints, Iterator, List, Sequence, Set, Union


class Argument:
    def __init__(self, name: str, has_default: bool, type_hint):
        self.name = name
        self.has_default = has_default
        self.type_hint = type_hint

    def __repr__(self):
        type_hint = getattr(self.type_hint, "__name__", repr(self.type_hint))
        common = f'{self.name}:{type_hint}'
        return common + " = ?" if self.has_default else common


class Arguments:
    """ Used when generating the injection wrapper """

    @classmethod
    def from_callable(cls,
                      func: Union[Callable, staticmethod, classmethod]
                      ) -> 'Arguments':
        if not (callable(func) or isinstance(func, (staticmethod, classmethod))):
            raise TypeError(f"func must be a callable or a static/class-method. "
                            f"Not a {type(func)}")
        unbound_method = is_unbound_method(func)  # doing it before un-wrapping.
        if isinstance(func, (staticmethod, classmethod)):
            func = func.__func__
        return cls._build(func, unbound_method)

    @classmethod
    def _build(cls, func: Callable, unbound_method: bool) -> 'Arguments':
        arguments: List[Argument] = []
        has_var_positional = False
        has_var_keyword = False

        # typing is used, as lazy evaluation is not done properly with Signature.
        type_hints = get_type_hints(func)

        for name, parameter in inspect.signature(func).parameters.items():
            if parameter.kind is parameter.VAR_POSITIONAL:
                has_var_positional = True
            elif parameter.kind is parameter.VAR_KEYWORD:
                has_var_keyword = True
            else:
                arguments.append(Argument(
                    name=name,
                    has_default=parameter.default is not parameter.empty,
                    type_hint=type_hints.get(name)
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
        self.name_to_argument = dict(((arg.name, arg)
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
        return set(self.name_to_argument.keys())

    def __repr__(self):
        args = [repr(arg) for arg in self.name_to_argument.values()]
        if self.has_var_positional:
            args.append("*args")
        if self.has_var_keyword:
            args.append("**kwargs")

        return f"Arguments({', '.join(args)})"

    def __getitem__(self, index: Union[str, int]) -> Argument:
        if isinstance(index, str):
            return self.name_to_argument[index]
        elif isinstance(index, int):
            return self.arguments[index]
        else:
            raise TypeError(f"Unsupported index {index!r}")

    def __contains__(self, name):
        return name in self.name_to_argument

    def __len__(self):
        return len(self.arguments)

    def __iter__(self) -> Iterator[Argument]:
        return iter(self.arguments)


def is_unbound_method(func: Union[Callable, staticmethod, classmethod]) -> bool:
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
