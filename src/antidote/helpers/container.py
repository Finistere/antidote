import contextlib
from typing import Iterable, Mapping

from .._internal.global_container import get_global_container, set_global_container
from ..container import DependencyContainer, ProxyContainer
from ..providers import FactoryProvider, GetterProvider, TagProvider


def new_container() -> DependencyContainer:
    container = DependencyContainer()
    container.register_provider(FactoryProvider())
    container.register_provider(GetterProvider())
    container.register_provider(TagProvider(container))

    return container


@contextlib.contextmanager
def context(dependencies: Mapping = None,
            include: Iterable = None,
            exclude: Iterable = None,
            missing: Iterable = None):
    """
    Creates a context within one can control which of the defined
    dependencies available or not. Any changes will be discarded at the
    end.

    >>> import antidote
    >>> with antidote.context(include=[]):
    ...     # Your code isolated from every other dependencies
    ...     antidote.container[DependencyContainer]
    <... DependencyContainer ...>

    The :py:class:`~antidote.DependencyInjector` and the
    :py:class:`~antidote.DependencyContainer` will still be accessible.

    Args:
        dependencies: Dependencies instances used to override existing ones
            in the new context.
        include: Iterable of dependencies to include. If None
            everything is accessible.
        exclude: Iterable of dependencies to exclude.
        missing: Iterable of dependencies which should raise a
            :py:exc:`~.exceptions.DependencyNotFoundError` even if a
            provider could instantiate them.

    """
    original_container = get_global_container()
    container = ProxyContainer(container=original_container or new_container(),
                               dependencies=dependencies,
                               include=include,
                               exclude=exclude,
                               missing=missing)

    set_global_container(container)
    try:
        yield
    finally:
        set_global_container(original_container)
