from typing import Optional

from ._internal import API
from .core import Scope
from .core.injection import validate_injection

__all__ = ['is_compiled', 'validate_injection', 'validated_scope']


@API.public
def is_compiled() -> bool:
    """
    Whether current Antidote implementations is the compiled (Cython) version or not
    """
    from ._internal.wrapper import compiled
    return compiled


@API.public
def validated_scope(scope: Optional[Scope] = Scope.sentinel(),
                    singleton: Optional[bool] = None,
                    *,
                    default: Optional[Scope]) -> Optional[Scope]:
    """
    Validates given arguments and ensures consistency between singleton and scope.

    Top-level APIs exposes both singleton and scope arguments. Users can choose either,
    but not both. This function does all validation necessary in those APIs.

    .. doctest:: utils_validated_scope

        >>> from antidote import Scope, world
        >>> from antidote.utils import validated_scope
        >>> custom_scope = world.scopes.new(name='custom')
        >>> validated_scope(singleton=None, default=custom_scope)
        Scope(name='custom')
        >>> validated_scope(singleton=True, default=None)
        Scope(name='singleton')
        >>> validated_scope(scope=Scope.singleton(), default=None)
        Scope(name='singleton')

    Args:
        scope: Scope argument to validate. Neutral value is :py:meth:`.Scope.sentinel`.
        singleton: Singleton argument to validate. Neutral value is :py:obj:`None`.
        default: Default value to use if both scope and singleton have neutral values.

    Returns:
        Scope defined by either :code:`singleton` or :code:`scope`.

    """
    if not (scope is None or isinstance(scope, Scope)):
        raise TypeError(f"scope must be a Scope or None, not {type(scope)}")
    if not (default is None or isinstance(default, Scope)):
        raise TypeError(f"default must be a Scope or None, not {type(default)}")

    if isinstance(singleton, bool):
        if scope is not Scope.sentinel():
            raise TypeError("Use either singleton or scope argument, not both.")
        return Scope.singleton() if singleton else None
    if singleton is not None:
        raise TypeError(f"singleton must be a boolean or None, "
                        f"not {type(singleton)}")

    return default if scope is Scope.sentinel() else scope
