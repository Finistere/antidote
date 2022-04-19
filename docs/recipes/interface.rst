Interface & Implementations
===========================

An interface defines a contract which should be respected by the implementation. It can be declared
with :py:func:`.interface` and implementations with :py:class:`.implements`:

.. testcode:: recipes_interface

    from antidote import interface, implements

    @interface
    class Command:
        def run(self) -> int:
            ...

    @implements(Command)
    class CommandImpl(Command):
        def run(self) -> int:
            return 0

:code:`Command` can also be a :py:class:`~typing.Protocol`. If it's :py:func:`~typing.runtime_checkable`,
it'll be enforced at runtime. The implementation can then be retrieved as if :code:`Command` was a
regular service:

.. doctest:: recipes_interface

    >>> from antidote import inject, world
    >>> @inject
    ... def cmd(command: Command = inject.me()) -> Command:
    ...     return command
    >>> cmd()
    <CommandImpl object at ...>
    >>> world.get(Command)
    <CommandImpl object at ...>


Overriding
----------

Any implementation can be overridden. The supplied implementation will be used in exactly the
same conditions as the original ones.

.. testcode:: recipes_interface_override

    from antidote import interface, implements

    @interface
    class Command:
        def run(self) -> int:
            ...

    @implements(Command)
    class CommandImpl(Command):
        def run(self) -> int:
            return 0


    @implements(Command).overriding(CommandImpl)
    class MyCommand(Command):
        def run(self) -> int:
            return 1

.. doctest:: recipes_interface_override

    >>> from antidote import inject, world
    >>> @inject
    ... def run(command: Command = inject.me()) -> int:
    ...     return command.run()
    >>> run()
    1


Default
-------

A default implementation can be specified for any interface. Any alternative implementation will
be preferred. The default implementation can only be changed with :py:meth:`.implements.overriding`.

.. testcode:: recipes_interface_default

    from antidote import interface, implements

    @interface
    class Command:
        def run(self) -> int:
            ...

    @implements(Command).by_default
    class DefaultCommand(Command):
        def run(self) -> int:
            return 0


Qualifiers
----------

When working with multiple implementations for an interface qualifiers offer an easy way to
distinguish them:


.. testcode:: recipes_interface_qualifiers

    from enum import auto, Enum
    from typing import Protocol

    from antidote import implements, interface


    class Event(Enum):
        START = auto()
        INITIALIZATION = auto()
        RELOAD = auto()
        SHUTDOWN = auto()


    @interface
    class Hook(Protocol):
        def run(self, event: Event) -> None:
            ...


    @implements(Hook).when(qualified_by=Event.START)
    class StartUpHook:
        def run(self, event: Event) -> None:
            pass


    @implements(Hook).when(qualified_by=[Event.INITIALIZATION,
                                         Event.RELOAD])
    class OnAnyUpdateHook:
        def run(self, event: Event) -> None:
            pass


    @implements(Hook).when(qualified_by=list(Event))
    class LogAnyEventHook:
        def run(self, event: Event) -> None:
            pass

.. note::

    For Python <3.9 you can use the following trick or create your own :code:`implements_when()`
    wrapper.

    .. testsetup:: recipes_interface_qualifiers_python_compat

        from typing import Protocol
        from antidote import implements, interface

        class Event:
            START = object()

        @interface
        class Hook(Protocol):
            def run(self, event: Event) -> None:
                ...

    .. testcode:: recipes_interface_qualifiers_python_compat

        from typing import TypeVar

        T = TypeVar('T')

        def _(x: T) -> T:
            return x

        @_(implements(Hook).when(qualified_by=Event.START))
        class StartUpHook:
            def run(self, event: Event) -> None:
                pass


Now Antidote will raise an error if one tries to use :code:`LifeCycleHook` like a service:

.. doctest:: recipes_interface_qualifiers

    >>> from antidote import world
    >>> world.get(Hook)
    Traceback (most recent call last):
      File "<stdin>", line 1, in ?
    DependencyInstantiationError: ...

To retrieve a single implementation you can use:

.. doctest:: recipes_interface_qualifiers

    >>> from antidote import inject
    >>> world.get[Hook].single(qualified_by=Event.SHUTDOWN)
    <LogAnyEventHook object at ...>
    >>> @inject
    ... def single_hook(hook: Hook = inject.me(qualified_by=Event.SHUTDOWN)
    ...                 ) -> Hook:
    ...     return hook
    >>> single_hook()
    <LogAnyEventHook object at ...>
    >>> @inject
    ... def single_hook2(hook = inject.get[Hook].single(qualified_by=Event.SHUTDOWN)
    ...                  ) -> Hook:
    ...     return hook
    >>> single_hook2()
    <LogAnyEventHook object at ...>

And to retrieve multiple of them:

.. doctest:: recipes_interface_qualifiers

    >>> world.get[Hook].all(qualified_by=Event.START)
    [<LogAnyEventHook object at ...>, <StartUpHook object at ...>]
    >>> @inject
    ... def all_hooks(hook: list[Hook] = inject.me(qualified_by=Event.START)
    ...               ) -> list[Hook]:
    ...     return hook
    >>> all_hooks()
    [<LogAnyEventHook object at ...>, <StartUpHook object at ...>]
    >>> @inject
    ... def all_hooks2(hook = inject.get[Hook].all(qualified_by=Event.START)
    ...                ) -> list[Hook]:
    ...     return hook
    >>> all_hooks2()
    [<LogAnyEventHook object at ...>, <StartUpHook object at ...>]

It's also possible to define more complex constraints, see :py:meth:`~.core.getter.TypedDependencyGetter.single` for example
and :py:class:`.QualifiedBy`.



