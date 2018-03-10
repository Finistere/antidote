import functools
from operator import getitem

from ..container import Dependency
from ..exceptions import DependencyNotProvidableError


class ParameterProvider(object):
    def __init__(self):
        self._parser_parameters = []

    def __antidote_provide__(self, dependency_id, type=None, *args, **kwargs):
        for parser, parameters in self._parser_parameters:
            keys = parser(dependency_id)
            if keys is not None:
                try:
                    param = rgetitem(parameters, keys)
                except (KeyError, TypeError):
                    pass
                else:
                    if type is not None:
                        param = type(param)

                    return Dependency(param, singleton=True)

        raise DependencyNotProvidableError(dependency_id)

    def register(self, parser, parameters):
        self._parser_parameters.append((parser, parameters))


def rgetitem(obj, items):
    return functools.reduce(getitem, items, obj)
