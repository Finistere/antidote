import contextlib
from typing import Iterable, Mapping

from .._internal.default_container import get_default_container, set_default_container
from ..core import DependencyContainer, ProxyContainer
from ..providers import ServiceProvider, ResourceProvider, TagProvider


def new_container() -> DependencyContainer:
    container = DependencyContainer()
    container.register_provider(ServiceProvider(container))
    container.register_provider(ResourceProvider(container))
    container.register_provider(TagProvider(container))

    return container


@contextlib.contextmanager
def context(*,
            dependencies: Mapping = None,
            include: Iterable = None,
            exclude: Iterable = None,
            missing: Iterable = None):
    """
    Creates a context within one can control which of the defined
    dependencies available or not. Any changes will be discarded at the
    end.

    .. doctest::

        >>> import antidote
        >>> with antidote.context(include=[]):
        ...     # Your code isolated from every other dependencies
        ...     pass

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
    original_container = get_default_container()
    container = ProxyContainer(container=original_container or new_container(),
                               dependencies=dependencies,
                               include=include,
                               exclude=exclude,
                               missing=missing)

    set_default_container(container)
    try:
        yield
    finally:
        set_default_container(original_container)
