import functools
from operator import getitem

from ..container import Dependency
from ..exceptions import DependencyNotProvidableError


class ParameterProvider(object):
    def __init__(self):
        self._parser_parameters = []

    def __antidote_provide__(self, dependency_id, *args, **kwargs):
        for parser, parameters in self._parser_parameters:
            key = parser(dependency_id)
            if key is not None:
                try:
                    param = rgetitem(parameters, key)
                except KeyError:
                    pass
                else:
                    return Dependency(param, singleton=True)

        raise DependencyNotProvidableError(dependency_id)

    def register(self, parser, parameters):
        self._parser_parameters.append((parser, parameters))


def rgetitem(obj, items):
    return functools.reduce(getitem, items, obj)
