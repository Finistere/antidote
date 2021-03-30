import collections.abc as c_abc
import inspect
from typing import (Any, Callable, Hashable, Iterable, Mapping, Optional, Sequence,
                    TypeVar, Union, overload)

from .._compatibility.typing import final
from .._internal import API
from .._internal.utils import FinalImmutable

F = TypeVar('F', bound=Callable[..., Any])
AnyF = Union[Callable[..., Any], staticmethod, classmethod]


@API.public
@final
class Arg(FinalImmutable):
    """
    Represents an argument (name and type hint) if you need a very custom injection
    logic.
    """
    __slots__ = ('name', 'type_hint', 'type_hint_with_extras')
    name: str
    """Name of the argument"""
    type_hint: Any
    """Type hint of the argument if any"""
    type_hint_with_extras: Any
    """
    Type hint of the argument if any with include_extras=True, so with annotations.
    """


# API.experimental
DEPENDENCIES_TYPE = Optional[Union[
    Mapping[str, Hashable],  # {arg_name: dependency, ...}
    Sequence[Optional[Hashable]],  # (dependency for arg 1, ...)
    Callable[[Arg], Optional[Hashable]],  # arg -> dependency
]]


@overload
def inject(__arg: staticmethod,  # noqa: E704  # pragma: no cover
           *,
           dependencies: DEPENDENCIES_TYPE = None,
           auto_provide: Union[bool, Iterable[Hashable]] = None,
           strict_validation: bool = True
           ) -> staticmethod: ...


@overload
def inject(__arg: classmethod,  # noqa: E704  # pragma: no cover
           *,
           dependencies: DEPENDENCIES_TYPE = None,
           auto_provide: Union[bool, Iterable[Hashable]] = None,
           strict_validation: bool = True
           ) -> classmethod: ...


@overload
def inject(__arg: F,  # noqa: E704  # pragma: no cover
           *,
           dependencies: DEPENDENCIES_TYPE = None,
           auto_provide: Union[bool, Iterable[Hashable]] = None,
           strict_validation: bool = True
           ) -> F: ...


@overload
def inject(*,  # noqa: E704  # pragma: no cover
           dependencies: DEPENDENCIES_TYPE = None,
           auto_provide: Union[bool, Iterable[Hashable]] = None,
           strict_validation: bool = True
           ) -> Callable[[F], F]: ...


@overload
def inject(__arg: Sequence[Hashable],  # noqa: E704  # pragma: no cover
           *,
           auto_provide: Union[bool, Iterable[Hashable]] = None,
           strict_validation: bool = True
           ) -> Callable[[F], F]: ...


@overload
def inject(__arg: Mapping[str, Hashable],  # noqa: E704  # pragma: no cover
           *,
           auto_provide: Union[bool, Iterable[Hashable]] = None,
           strict_validation: bool = True
           ) -> Callable[[F], F]: ...


@API.public
def inject(__arg: Union[AnyF, Sequence[Hashable], Mapping[str, Hashable]] = None,
           *,
           dependencies: DEPENDENCIES_TYPE = None,
           auto_provide: Union[bool, Iterable[Hashable]] = None,
           strict_validation: bool = True
           ) -> AnyF:
    """
    Inject the dependencies into the function lazily, they are only retrieved
    upon execution. As several options can apply to the same argument, the priority is
    defined as:

    1. Annotated type hints (PEP-593)
    2. Dependencies declared explicitly if any declared with :code:`dependencies`.
    3. Class type hints if specified with :code:`auto_provide`.

    .. doctest:: core_inject

        >>> from antidote import inject, Service, Provide
        >>> class A(Service):
        ...     pass
        >>> class B(Service):
        ...     pass
        >>> # PEP-593 annotation
        ... @inject
        ... def f(a: Provide[A]):
        ...     pass # a = world.get(A)
        >>> # All possibilities for dependency argument.
        >>> @inject(dependencies=dict(b='dependency'))
        ... def f(a, b):
        ...     pass  # a, b = <not injected>, world.get('dependency')
        >>> @inject(dict(b='dependency'))  # shortcut
        ... def f(a, b):
        ...     pass
        >>> @inject(dependencies=[None, 'dependency'])  # `a` is ignored
        ... def f(a, b):
        ...     pass  # a, b = <not injected>, world.get('dependency')
        >>> @inject([None, 'dependency'])  # shortcut
        ... def f(a, b):
        ...     pass  # a, b = <not injected>, world.get('dependency')
        >>> @inject(dependencies=lambda arg: 'dependency' if arg.name == 'b' else None)
        ... def f(a, b):
        ...     pass  # a, b = <not injected>, world.get('dependency')
        >>> # All possibilities for auto_provide argument.
        >>> @inject(auto_provide=True)
        ... def f(a: A):
        ...     pass  # a = world.get(A)
        >>> @inject(auto_provide=[B])
        ... def f(a: A, b: B):
        ...     pass  # a, b = <not injected>, world.get(B)
        >>> @inject(auto_provide=False)  # default
        ... def f(a: A):
        ...     pass  # a = <not injected>

    Args:
        __arg: Callable to be wrapped. Can also be used on static methods or class
            methods. May also be sequence of dependencies or mapping from argument
            name to dependencies.
        dependencies: Explicit definition of the dependencies which overrides
            :code:`auto_provide`. Defaults to :py:obj:`None`.
            Can be one of:

            - Mapping from argument name to its dependency
            - Sequence of dependencies which will be mapped with the position
              of the arguments. :py:obj:`None` can be used as a placeholder.
            - Callable which receives :py:class:`~.Arg` as arguments and should
              return the matching dependency. :py:obj:`None` should be used for
              arguments without dependency.
            - String which must have :code:`{arg_name}` as format parameter
        auto_provide: Whether or not the type hints should be used as the arguments
            dependency. An iterable of argument names may also be supplied to activate
            this feature only for those. Any type hints from the builtins (str, int...)
            or the typing (except :py:class:`~typing.Optional`) are ignored.
            Defaults to :code:`False`.

    Returns:
        The decorator to be applied or the injected function if the
        argument :code:`func` was supplied.

    """

    from ._injection import raw_inject

    if isinstance(__arg, (c_abc.Sequence, c_abc.Mapping)):
        if isinstance(__arg, str):
            raise TypeError("First argument must be an sequence/mapping of dependencies "
                            "or the function to be wrapped, not a string.")
        if dependencies is not None:
            raise TypeError("dependencies must be None if a sequence/mapping of "
                            "dependencies is provided as first argument.")
        dependencies = __arg
        __arg = None

    def decorate(f: AnyF) -> AnyF:
        return raw_inject(
            f,
            dependencies=dependencies,
            auto_provide=auto_provide if auto_provide is not None else False,
            strict_validation=strict_validation)

    return __arg and decorate(__arg) or decorate


@API.public  # Function will be kept in sync with @inject, so you may use it.
def validate_injection(dependencies: DEPENDENCIES_TYPE = None,
                       auto_provide: Union[bool, Iterable[Hashable]] = None) -> None:
    """
    Validates that injection parameters are valid. If not, an error is raised.

    .. doctest:: core_injection_validate_injection

        >>> from antidote.utils import validate_injection
        >>> validate_injection(auto_provide=True)
        >>> validate_injection(auto_provide=object())
        Traceback (most recent call last):
          File "<stdin>", line 1, in ?
        TypeError: auto_provide must be either a boolean or an iterable of classes ...


    Args:
        dependencies: As defined by :py:func:`~.injection.inject`
        auto_provide: As defined by  :py:func:`~.injection.inject`
    """
    if not (dependencies is None
            or (isinstance(dependencies, (c_abc.Sequence, c_abc.Mapping))
                and not isinstance(dependencies, str))
            or callable(dependencies)):
        raise TypeError(
            f"dependencies can be None, a mapping of arguments names to dependencies, "
            f"a sequence of dependencies, a function, "
            f"not a {type(dependencies)!r}"
        )
    if isinstance(dependencies, c_abc.Mapping):
        if not all(isinstance(k, str) for k in dependencies.keys()):
            raise TypeError("Dependencies keys must be argument names (str)")

    if isinstance(auto_provide, str) \
            or not (auto_provide is None
                    or isinstance(auto_provide, (bool, c_abc.Iterable))):
        raise TypeError(
            f"auto_provide must be either a boolean or an iterable of classes, "
            f"not {type(auto_provide)!r}.")

    # If we can iterate over it safely
    if isinstance(auto_provide, (list, set, tuple, frozenset)):
        for cls in auto_provide:
            if not (isinstance(cls, type) and inspect.isclass(cls)):
                raise TypeError(f"auto_provide must be a boolean or an iterable of "
                                f"classes, but contains {cls!r} which is not a class.")
