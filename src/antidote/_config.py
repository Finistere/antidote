from typing_extensions import final

from ._internal import API
from ._internal.utils.meta import Singleton


@API.public  # All of the methods are public, but the only support instance is the singleton config.
@final
class Config(Singleton):
    """
    Global configuration used by Antidote to (de-)activate features.
    """

    @property
    def auto_detect_type_hints_locals(self) -> bool:
        """
        .. versionadded:: 1.3

        Whether :py:func:`.inject`, :py:func:`.injectable`, :py:class:`.implements` and
        :py:func:`.wire` should rely on inspection to determine automatically the locals
        for their argument :code:`type_hints_locals` used for
        :py:func:`typing.get_type_hints`. Deactivated by default. If activated, inspection is only
        used when :code:`type_hints_locals` is not specified explitely.

        It's mostly interesting during tests. The following example wouldn't work with
        string annotations:

        .. doctest:: config_auto_detect_type_hints_locals

            >>> from __future__ import annotations
            >>> from antidote import config, injectable, inject, world
            >>> config.auto_detect_type_hints_locals = True
            >>> def dummy_test():
            ...     with world.test.new():
            ...         @injectable
            ...         class Dummy:
            ...             pass
            ...
            ...         @inject
            ...         def f(dummy: Dummy = inject.me()) -> Dummy:
            ...             return dummy
            ...
            ...         return f() is world.get(Dummy)
            >>> dummy_test()
            True

        .. testcleanup:: config_auto_detect_type_hints_locals

            config.auto_detect_type_hints_locals = False

        """
        return bool(getattr(self, "__type_hints_locals", False))

    @auto_detect_type_hints_locals.setter
    def auto_detect_type_hints_locals(self, value: bool) -> None:
        if not isinstance(value, bool):
            raise TypeError(f"auto_detect_type_hints_locals must be a boolean, "
                            f"not a {type(value)}.")
        setattr(self, "__type_hints_locals", value)


# API.public, but import it directly from antidote.
config = Config()
