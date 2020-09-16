from typing import Hashable, Optional, final

from ._provider import _FREEZE_ATTR_NAME, ProviderMeta
from .container import DependencyContainer, DependencyInstance, RawDependencyProvider
from .._internal import API


@API.public
def does_not_freeze(method):
    """
    Decorated methods won't freeze when :py:func:`~antidote.world.freeze` is called
    """
    setattr(method, _FREEZE_ATTR_NAME, False)
    return method


@API.public
class DependencyProvider(RawDependencyProvider,
                         metaclass=ProviderMeta,
                         # reserved
                         abstract=True):
    """
    Abstract Base class for a provider.

    Consider using :py:class:`~.StatelessDependencyProvider` if you do not have any state
    to keep.

    .. doctest::

        >>> from typing import Hashable, Optional
        >>> from antidote import world
        >>> from antidote.core import DependencyProvider, DependencyContainer, \
        ...     DependencyInstance, does_not_freeze
        >>> @world.provider
        ... class SquareProvider(DependencyProvider):
        ...     def __init__(self, registered: set = None):
        ...         super().__init__()
        ...         self._registered = registered or set()
        ...
        ...     def register_numbers(self, *numbers: int):
        ...         self._registered |= set(numbers)
        ...
        ...     def provide(self, dependency: Hashable, container: DependencyContainer
        ...                 ) -> Optional[DependencyInstance]:
        ...         if isinstance(dependency, int) and dependency in self._registered:
        ...             return DependencyInstance(self.square(dependency), singleton=True)
        ...
        ...     # we don't want this method to fail when world freezes
        ...     # and it does not modify any state, so we're safe !
        ...     @does_not_freeze
        ...     def square(self, n: int) -> int:
        ...         return n ** 2
        ...
        ...     def copy(self) -> 'SquareProvider':
        ...         return SquareProvider(self._registered.clone())
        >>> # To modify your provider, retrieve it from world
        ... world.get[SquareProvider]().register_numbers(7, 9)
        ... world.get(9)
        81
        >>> # If you freeze world, you cannot register any dependencies
        ... world.freeze()
        ... world.get[SquareProvider]().register_numbers(10)
        FrozenWorldError
        >>> # But you can still retrieve previously defined ones
        ... world.get(9)
        91
        >>> # even if never called before
        ... world.get(7)
        49


    .. warning::
        This is most advanced feature of Antidote and allows you to extend Antidote's
        behavior. So be careful with it, it will impact the whole library. There are
        several rules to respect:

        1. Different providers MUST provide strictly different dependencies.
        2. You MUST NOT use :py:mod:`~antidote.world`. If you need a dependency, rely on
           the provided :py:class:`~.core.container.DependencyContainer`.
        3. Methods will automatically freeze except those marked with the decorator
           :py:func:`~.does_not_freeze`. You may only use it on methods which do NOT
           modify the provider or methods only called by ones that are frozen.
           :py:meth:`~.provide` and :py:meth:`~.clone` are the only methods that are not
           affected.
        4. You may cache singletons by yourself, but you need to clean your cache when
           :py:meth:`~.clone` is called with :code:`keep_singletons_cache=False`.
    """
    __antidote__ = None  # reserved

    def provide(self, dependency: Hashable, container: DependencyContainer
                ) -> Optional[DependencyInstance]:
        """
        Method called by the :py:class:`~.core.container.DependencyContainer` when
        searching for a dependency. Be sure that the dependency space of your
        providers don't intersect !

        If you need to access other dependencies, you MUST use the provided
        :code:`container` argument and NEVER :py:mod:`~antidote.world`.

        It is recommended to check quickly if the dependency can be provided or
        not, as :py:class:`~.core.container.DependencyContainer` will try all of its
        registered providers.

        It is always called within a thread-safe (locked) environment, so you
        don't need to worry about it. You also don't need to worry about
        handling singletons, the :py:class:`~.core.container.DependencyContainer` will
        handle it for you.

        Args:
            dependency (Hashable): The dependency to be provided by the provider.
            container (DependencyContainer): current container which may use to retrieve
                other dependencies.

        Returns:
            DependencyInstance:
                The requested instance wrapped in a
                :py:class:`~.core.container.DependencyInstance` if available or
                :py:obj:`None`. If the dependency is a singleton, you MUST specify it
                with :code:`singleton=True`.
        """
        raise NotImplementedError()  # pragma: no cover

    def clone(self, keep_singletons_cache: bool) -> 'DependencyProvider':
        """
        If you have no internal state, consider implementing
        :py:class:`~.StatelessDependencyProvider` instead.

        Used by the different test utilities.

        Returns:
            A deep copy of the current provider. It should always be a new instance.
        """
        raise NotImplementedError()  # pragma: no cover

    @API.public_for_tests
    @does_not_freeze
    @final
    def test_provide(self, dependency: Hashable):
        """
        Method only used for tests to avoid the injection of the current
        :py:class:`~.core.container.DependencyContainer`. It will never be used by
        Antidote and you should NOT rely on it.
        """
        from .._internal.state import get_container
        return self.provide(dependency, get_container())


@API.public
class StatelessDependencyProvider(DependencyProvider, abstract=True):
    """
    Abstract stateless :py:class:`~.DependencyProvider` which
    implements :py:meth:`~.clone`.

    .. doctest::

        >>> from typing import Hashable, Optional
        >>> from antidote import world
        >>> from antidote.core import DependencyProvider, DependencyContainer, \
        ...     DependencyInstance
        >>> @world.provider
        ... class SquareProvider(StatelessDependencyProvider):
        ...     def provide(self, dependency: Hashable, container: DependencyContainer
        ...                 ) -> Optional[DependencyInstance]:
        ...         if isinstance(dependency, int):
        ...             return DependencyInstance(dependency ** 2, singleton=True)
        >>> world.get(9)
        81

    """

    @final
    def clone(self, keep_singletons_cache: bool) -> 'StatelessDependencyProvider':
        return type(self)()
