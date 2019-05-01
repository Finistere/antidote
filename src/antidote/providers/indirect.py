from enum import Flag
from typing import Any, Dict, List, Optional

from .._internal.utils import SlotsReprMixin
from ..core import DependencyInstance, DependencyProvider
from ..exceptions import DuplicateDependencyError, UndefinedContextError


class ContextualTarget(SlotsReprMixin):
    """
    Internal API
    """
    __slots__ = ('context', 'target_dependency')

    def __init__(self, context: Flag, target_dependency: Any):
        self.context = context
        self.target_dependency = target_dependency


class ContextualLink(SlotsReprMixin):
    """
    Internal API
    """
    __slots__ = ('context_dependency', '_targets')

    def __init__(self, context_dependency: Any):
        self.context_dependency = context_dependency
        self._targets: List[ContextualTarget] = list()

    def add(self, context: Flag, target_dependency: Any):
        self._targets.append(ContextualTarget(context, target_dependency))

    def get(self, context: Flag) -> Optional[Any]:
        for implementation in self._targets:
            if context in implementation.context:
                return implementation.target_dependency

        return None


class IndirectProvider(DependencyProvider):
    def __init__(self, container):
        super(IndirectProvider, self).__init__(container)
        self._contextual_links: Dict[Any, ContextualLink] = dict()
        self._links: Dict[Any, Any] = dict()

    def provide(self, dependency) -> Optional[DependencyInstance]:
        try:
            target_dependency = self._links[dependency]
        except KeyError:
            try:
                contextual_link = self._contextual_links[dependency]
            except KeyError:
                return None
            else:
                current_context = self._container.safe_provide(
                    contextual_link.context_dependency
                )

                target_dependency = contextual_link.get(current_context.instance)
                if target_dependency is None:
                    raise UndefinedContextError(dependency, current_context.instance)

                target = self._container.safe_provide(target_dependency)
                return DependencyInstance(
                    target.instance,
                    singleton=current_context.singleton & target.singleton
                )
        else:
            return self._container.provide(target_dependency)

    def register(self, dependency: Any, target_dependency: Any, context: Flag = None):
        if dependency in self._links:
            raise DuplicateDependencyError(dependency,
                                           self._links[dependency])

        if context is None:
            if dependency in self._contextual_links:
                raise DuplicateDependencyError(dependency,
                                               self._contextual_links[dependency])
            self._links[dependency] = target_dependency
        elif isinstance(context, Flag):
            try:
                contextual_link = self._contextual_links[dependency]
            except KeyError:
                contextual_link = ContextualLink(type(context))
                self._contextual_links[dependency] = contextual_link

            existing_target = contextual_link.get(context)
            if existing_target is not None:
                raise DuplicateDependencyError((dependency, context), existing_target)

            contextual_link.add(context, target_dependency)
        else:
            raise TypeError(f"profile must be an instance of Flag or be None, "
                            f"not a {type(context)!r}")
