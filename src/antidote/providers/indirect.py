from enum import Enum
from typing import Dict, Hashable, Optional

from .._internal.utils import SlotsReprMixin
from ..core import DependencyInstance, DependencyProvider
from ..exceptions import DuplicateDependencyError, UndefinedContextError


class IndirectProvider(DependencyProvider):
    """
    IndirectProvider
    """

    def __init__(self, container):
        super(IndirectProvider, self).__init__(container)
        self._stateful_links = dict()  # type: Dict[Hashable, StatefulLink]
        self._links = dict()  # type: Dict[Hashable, Hashable]

    def provide(self, dependency: Hashable) -> Optional[DependencyInstance]:
        try:
            target = self._links[dependency]
        except KeyError:
            try:
                stateful_link = self._stateful_links[dependency]
            except KeyError:
                return None
            else:
                state = self._container.safe_provide(
                    stateful_link.state_dependency
                )

                try:
                    target = stateful_link.targets[state.instance]
                except KeyError:
                    raise UndefinedContextError(dependency, state.instance)

                t = self._container.safe_provide(target)
                return DependencyInstance(
                    t.instance,
                    singleton=state.singleton & t.singleton
                )
        else:
            return self._container.safe_provide(target)

    def register(self, dependency: Hashable, target_dependency: Hashable,
                 state: Enum = None):
        if dependency in self._links:
            raise DuplicateDependencyError(dependency,
                                           self._links[dependency])

        if state is None:
            if dependency in self._stateful_links:
                raise DuplicateDependencyError(dependency,
                                               self._stateful_links[dependency])
            self._links[dependency] = target_dependency
        elif isinstance(state, Enum):
            try:
                stateful_link = self._stateful_links[dependency]
            except KeyError:
                stateful_link = StatefulLink(type(state))
                self._stateful_links[dependency] = stateful_link

            if state in stateful_link.targets:
                raise DuplicateDependencyError((dependency, state),
                                               stateful_link.targets[state])

            stateful_link.targets[state] = target_dependency
        else:
            raise TypeError("profile must be an instance of Flag or be None, "
                            "not a {!r}".format(type(state)))


class StatefulLink(SlotsReprMixin):
    """
    Internal API
    """
    __slots__ = ('state_dependency', 'targets')

    def __init__(self, state_dependency: Hashable):
        self.state_dependency = state_dependency
        self.targets = dict()  # type: Dict[Enum, Hashable]
