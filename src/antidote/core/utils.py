from typing import final, Generic, Hashable, TypeVar

from .._internal.utils import FinalImmutable
from .._internal import API

T = TypeVar('T')


@API.public
@final
class Dependency(FinalImmutable, Generic[T]):
    """
    Used to clearly state that a value should be treated as a dependency and must
    be retrieved from Antidote. It is recommended to use it through
    :py:func:`~antidote.world.lazy` as presented:

    .. doctest::

        >>> from antidote import world
        >>> world.singletons.set('dependency', 1)
        >>> world.lazy('dependency')
        Dependency(value='dependency')
        >>> # to retrieve the dependency later, you may use get()
        ... world.lazy[int]('dependency').get()
        1

    """
    __slots__ = ('value',)
    value: Hashable
    """Dependency to be retrieved"""

    def __init__(self, value):
        super().__init__(value=value)

    def get(self) -> T:
        """
        Returns:
            dependency instance retrieved from :py:mod:`~antidote.world`.
        """
        from antidote import world
        return world.get[T](self.value)
