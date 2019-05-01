from enum import Enum
from typing import Any, Dict, Optional

from .._internal.utils import SlotsReprMixin
from ..core import DependencyInstance, DependencyProvider
from ..exceptions import DuplicateDependencyError, UndefinedContextError


class IndirectProvider(DependencyProvider):
    """
    IndirectProvider
    """

    def __init__(self, container):
        super(IndirectProvider, self).__init__(container)
        self._contextual_links = dict()  # type: Dict[Any, ContextualLink]
        self._links = dict()  # type: Dict[Any, Any]

    def provide(self, dependency) -> Optional[DependencyInstance]:
        try:
            target = self._links[dependency]
        except KeyError:
            try:
                contextual_link = self._contextual_links[dependency]
            except KeyError:
                return None
            else:
                current_context = self._container.safe_provide(
                    contextual_link.context_dependency
                )

                try:
                    target = contextual_link.targets[current_context.instance]
                except KeyError:
                    raise UndefinedContextError(dependency, current_context.instance)

                t = self._container.safe_provide(target)
                return DependencyInstance(
                    t.instance,
                    singleton=current_context.singleton & t.singleton
                )
        else:
            return self._container.safe_provide(target)

    def register(self, dependency: Any, target_dependency: Any, context: Enum = None):
        if dependency in self._links:
            raise DuplicateDependencyError(dependency,
                                           self._links[dependency])

        if context is None:
            if dependency in self._contextual_links:
                raise DuplicateDependencyError(dependency,
                                               self._contextual_links[dependency])
            self._links[dependency] = target_dependency
        elif isinstance(context, Enum):
            try:
                contextual_link = self._contextual_links[dependency]
            except KeyError:
                contextual_link = ContextualLink(type(context))
                self._contextual_links[dependency] = contextual_link

            if context in contextual_link.targets:
                raise DuplicateDependencyError((dependency, context),
                                               contextual_link.targets[context])

            contextual_link.targets[context] = target_dependency
        else:
            raise TypeError("profile must be an instance of Flag or be None, "
                            "not a {!r}".format(type(context)))


class ContextualTarget(SlotsReprMixin):
    """
    Internal API
    """
    __slots__ = ('context', 'target_dependency')

    def __init__(self, context: Enum, target_dependency: Any):
        self.context = context
        self.target_dependency = target_dependency


class ContextualLink(SlotsReprMixin):
    """
    Internal API
    """
    __slots__ = ('context_dependency', 'targets')

    def __init__(self, context_dependency: Any):
        self.context_dependency = context_dependency
        self.targets = dict()  # type: Dict[Enum, Any]
