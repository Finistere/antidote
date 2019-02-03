import inspect
from collections import OrderedDict
from typing import Callable, get_type_hints, Iterator, Sequence, Union


class Argument:
    def __init__(self, name: str, has_default: bool, type_hint):
        self.name = name
        self.has_default = has_default
        self.type_hint = type_hint


class Arguments:
    @classmethod
    def from_method(cls,
                    func: Union[Callable, staticmethod, classmethod]
                    ) -> 'Arguments':
        if isinstance(func, (staticmethod, classmethod)):
            func = func.__func__
        return cls.from_callable(func)

    @classmethod
    def from_callable(cls, func: Callable) -> 'Arguments':
        arguments = []
        has_var_positional = False
        has_var_keyword = False

        try:
            # typing is used, as lazy evaluation is not done properly with Signature.
            type_hints = get_type_hints(func)
        except Exception:  # Python 3.5.3 does not handle properly method wrappers
            type_hints = {}

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
                         has_var_keyword=has_var_keyword)

    def __init__(self,
                 arguments: Sequence[Argument],
                 has_var_positional: bool,
                 has_var_keyword: bool):
        self.arguments_by_name = OrderedDict(((arg.name, arg)
                                              for arg in arguments))
        self.has_var_positional = has_var_positional
        self.has_var_keyword = has_var_keyword

    def __getitem__(self, name) -> Argument:
        return self.arguments_by_name[name]

    def __contains__(self, name):
        return name in self.arguments_by_name

    def __len__(self):
        return len(self.arguments_by_name)

    def __iter__(self) -> Iterator[Argument]:
        return iter(self.arguments_by_name.values())
