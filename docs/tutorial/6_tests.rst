6. Tests
========


Until now, you've seen that you could still use normally injected functions:

.. testcode:: tutorial_test

    from antidote import injectable, inject

    @injectable
    class MyService:
        pass

    @inject
    def f(my_service: MyService = inject.me()) -> MyService:
        return my_service

    # injected
    f()

    # manual override
    f(MyService())
    f(my_service=MyService())

This allows to test easily individual components in unit-tests. But in more complex tests it's usually
not enough. So Antidote provides additional tooling to isolate tests and change dependencies. The most
important of them is :py:func:`world.test.clone`. It'll create an isolated world with the same
dependencies declaration, but not the same instances!

.. doctest:: tutorial_test

    >>> from antidote import world
            >>> with world.test.clone():
            ...     # This works as expected !
            ...     my_service = f()
            >>> # but it's isolated from the rest, so you don't have the same instance
            ... my_service is world.get(MyService)
            False
            >>> dummy = object()
            >>> with world.test.copy():
            ...     # Override dependencies however you like
            ...     world.test.override.singleton(MyService, dummy)
            ...     f() is dummy
            True

        You can also use a factory to override dependencies:
            >>> with world.test.clone():
            ...     # This works as expected !
            ...     my_service = f()
            >>> # but it's isolated from the rest, so you don't have the same instance
            ... my_service is world.get(MyService)
            False
            >>> dummy = object()
            >>> with world.test.copy():
            ...     # Override dependencies however you like
            ...     world.test.override.singleton(MyService, dummy)
            ...     f() is dummy
            True

        You can also use a factory to override dependencies:
        >>> with world.test.clone():
        ...     # This works as expected !
        ...     my_service = f()
        >>> # but it's isolated from the rest, so you don't have the same instance
        ... my_service is world.get(MyService)
        False
        >>> dummy = object()
        >>> with world.test.copy():
        ...     # Override dependencies however you like
        ...     world.test.override.singleton(MyService, dummy)
        ...     f() is dummy
        True

    You can also use a factory to override dependencies:
            >>> with world.test.clone():
            ...     # This works as expected !
            ...     my_service = f()
            >>> # but it's isolated from the rest, so you don't have the same instance
            ... my_service is world.get(MyService)
            False
            >>> dummy = object()
            >>> with world.test.copy():
            ...     # Override dependencies however you like
            ...     world.test.override.singleton(MyService, dummy)
            ...     f() is dummy
            True

        You can also use a factory to override dependencies:
            >>> with world.test.clone():
            ...     # This works as expected !
            ...     my_service = f()
            >>> # but it's isolated from the rest, so you don't have the same instance
            ... my_service is world.get(MyService)
            False
            >>> dummy = object()
            >>> with world.test.copy():
            ...     # Override dependencies however you like
            ...     world.test.override.singleton(MyService, dummy)
            ...     f() is dummy
            True

        You can also use a factory to override dependencies:
        >>> with world.test.clone():
        ...     # This works as expected !
        ...     my_service = f()
        >>> # but it's isolated from the rest, so you don't have the same instance
        ... my_service is world.get(MyService)
        False
        >>> dummy = object()
        >>> with world.test.copy():
        ...     # Override dependencies however you like
        ...     world.test.override.singleton(MyService, dummy)
        ...     f() is dummy
        True

    You can also use a factory to override dependencies:
            >>> with world.test.clone():
            ...     # This works as expected !
            ...     my_service = f()
            >>> # but it's isolated from the rest, so you don't have the same instance
            ... my_service is world.get(MyService)
            False
            >>> dummy = object()
            >>> with world.test.copy():
            ...     # Override dependencies however you like
            ...     world.test.override.singleton(MyService, dummy)
            ...     f() is dummy
            True

        You can also use a factory to override dependencies:
            >>> with world.test.copy():
            ...     # This works as expected !
            ...     my_service = f()
            >>> # but it's isolated from the rest, so you don't have the same instance
            ... my_service is world.get(MyService)
            False
            >>> dummy = object()
            >>> with world.test.copy():
            ...     # Override dependencies however you like
            ...     world.test.override.singleton(MyService, dummy)
            ...     f() is dummy
            True

        You can also use a factory to override dependencies:
        >>> with world.test.clone():
        ...     # This works as expected !
        ...     my_service = f()
        >>> # but it's isolated from the rest, so you don't have the same instance
        ... my_service is world.get(MyService)
        False
        >>> dummy = object()
        >>> with world.test.clone():
        ...     # Override dependencies however you like
        ...     world.test.override.singleton(MyService, dummy)
        ...     f() is dummy
        True

    You can also use a factory to override dependencies:
            >>> with world.test.clone():
            ...     # This works as expected !
            ...     my_service = f()
            >>> # but it's isolated from the rest, so you don't have the same instance
            ... my_service is world.get(MyService)
            False
            >>> dummy = object()
            >>> with world.test.copy():
            ...     # Override dependencies however you like
            ...     world.test.override.singleton(MyService, dummy)
            ...     f() is dummy
            True

        You can also use a factory to override dependencies:
            >>> with world.test.copy():
            ...     # This works as expected !
            ...     my_service = f()
            >>> # but it's isolated from the rest, so you don't have the same instance
            ... my_service is world.get(MyService)
            False
            >>> dummy = object()
            >>> with world.test.copy():
            ...     # Override dependencies however you like
            ...     world.test.override.singleton(MyService, dummy)
            ...     f() is dummy
            True

        You can also use a factory to override dependencies:
        >>> with world.test.clone():
        ...     # This works as expected !
        ...     my_service = f()
        >>> # but it's isolated from the rest, so you don't have the same instance
        ... my_service is world.get(MyService)
        False
        >>> dummy = object()
        >>> with world.test.clone():
        ...     # Override dependencies however you like
        ...     world.test.override.singleton(MyService, dummy)
        ...     f() is dummy
        True

    You can also use a factory to override dependencies:
            >>> with world.test.clone():
            ...     # This works as expected !
            ...     my_service = f()
            >>> # but it's isolated from the rest, so you don't have the same instance
            ... my_service is world.get(MyService)
            False
            >>> dummy = object()
            >>> with world.test.copy():
            ...     # Override dependencies however you like
            ...     world.test.override.singleton(MyService, dummy)
            ...     f() is dummy
            True

        You can also use a factory to override dependencies:
            >>> with world.test.clone():
            ...     # This works as expected !
            ...     my_service = f()
            >>> # but it's isolated from the rest, so you don't have the same instance
            ... my_service is world.get(MyService)
            False
            >>> dummy = object()
            >>> with world.test.copy():
            ...     # Override dependencies however you like
            ...     world.test.override.singleton(MyService, dummy)
            ...     f() is dummy
            True

        You can also use a factory to override dependencies:
        >>> with world.test.copy():
        ...     # This works as expected !
        ...     my_service = f()
        >>> # but it's isolated from the rest, so you don't have the same instance
        ... my_service is world.get(MyService)
        False
        >>> dummy = object()
        >>> with world.test.clone():
        ...     # Override dependencies however you like
        ...     world.test.override.singleton(MyService, dummy)
        ...     f() is dummy
        True

    You can also use a factory to override dependencies:
            >>> with world.test.clone():
            ...     # This works as expected !
            ...     my_service = f()
            >>> # but it's isolated from the rest, so you don't have the same instance
            ... my_service is world.get(MyService)
            False
            >>> dummy = object()
            >>> with world.test.copy():
            ...     # Override dependencies however you like
            ...     world.test.override.singleton(MyService, dummy)
            ...     f() is dummy
            True

        You can also use a factory to override dependencies:
            >>> with world.test.clone():
            ...     # This works as expected !
            ...     my_service = f()
            >>> # but it's isolated from the rest, so you don't have the same instance
            ... my_service is world.get(MyService)
            False
            >>> dummy = object()
            >>> with world.test.copy():
            ...     # Override dependencies however you like
            ...     world.test.override.singleton(MyService, dummy)
            ...     f() is dummy
            True

        You can also use a factory to override dependencies:
        >>> with world.test.copy():
        ...     # This works as expected !
        ...     my_service = f()
        >>> # but it's isolated from the rest, so you don't have the same instance
        ... my_service is world.get(MyService)
        False
        >>> dummy = object()
        >>> with world.test.clone():
        ...     # Override dependencies however you like
        ...     world.test.override.singleton(MyService, dummy)
        ...     f() is dummy
        True

    You can also use a factory to override dependencies:
        >>> with world.test.clone():
        ...     # This works as expected !
        ...     my_service = f()
        >>> # but it's isolated from the rest, so you don't have the same instance
        ... my_service is world.get(MyService)
        False
        >>> dummy = object()
        >>> with world.test.copy():
        ...     # Override dependencies however you like
        ...     world.test.override.singleton(MyService, dummy)
        ...     f() is dummy
        True

    You can also use a factory to override dependencies:
        >>> with world.test.clone():
        ...     # This works as expected !
        ...     my_service = f()
        >>> # but it's isolated from the rest, so you don't have the same instance
        ... my_service is world.get(MyService)
        False
        >>> dummy = object()
        >>> with world.test.copy():
        ...     # Override dependencies however you like
        ...     world.test.override.singleton(MyService, dummy)
        ...     f() is dummy
        True

    You can also use a factory to override dependencies:
    >>> with world.test.clone():
    ...     # This works as expected !
    ...     my_service = f()
    >>> # but it's isolated from the rest, so you don't have the same instance
    ... my_service is world.get(MyService)
    False
    >>> dummy = object()
    >>> with world.test.clone():
    ...     # Override dependencies however you like
    ...     world.test.override.singleton(MyService, dummy)
    ...     f() is dummy
    True

You can also use a factory to override dependencies:

.. doctest:: tutorial_test

    >>> with world.test.copy():
        ...     @world.test.override.factory()
        ...     def override_my_service() -> MyService:
        ...         return dummy
        ...     f() is dummy
        True

    Overrides can be changed at will and override each other. You can also nest test worlds and keep
    the singletons you defined:
    ...     @world.test.override.factory()
    ...     def override_my_service() -> MyService:
    ...         return dummy
    ...     f() is dummy
    True

Overrides can be changed at will and override each other. You can also nest test worlds and keep
the singletons you defined:


.. doctest:: tutorial_test

    >>> with world.test.copy():
            ...     world.test.override.singleton(MyService, dummy)
            ...     # override twice MyService
            ...     world.test.override.singleton(MyService, dummy)
            ...     with world.test.clone():
            ...         f() is dummy
            False
            >>> with world.test.clone():
            ...     world.test.override.singleton(MyService, dummy)
            ...     with world.test.clone(keep_singletons=True):
            ...         f() is dummy
            True


        Beware that :py
            ...     world.test.override.singleton(MyService, dummy)
            ...     # override twice MyService
            ...     world.test.override.singleton(MyService, dummy)
            ...     with world.test.clone():
            ...         f() is dummy
            False
            >>> with world.test.copy():
            ...     world.test.override.singleton(MyService, dummy)
            ...     with world.test.clone(keep_singletons=True):
            ...         f() is dummy
            True


        Beware that :py
            ...     world.test.override.singleton(MyService, dummy)
            ...     # override twice MyService
            ...     world.test.override.singleton(MyService, dummy)
            ...     with world.test.clone():
            ...         f() is dummy
            False
            >>> with world.test.copy():
            ...     world.test.override.singleton(MyService, dummy)
            ...     with world.test.clone(keep_singletons=True):
            ...         f() is dummy
            True


        Beware that :py
        ...     world.test.override.singleton(MyService, dummy)
        ...     # override twice MyService
        ...     world.test.override.singleton(MyService, dummy)
        ...     with world.test.clone():
        ...         f() is dummy
        False
        >>> with world.test.copy():
        ...     world.test.override.singleton(MyService, dummy)
        ...     with world.test.clone(keep_singletons=True):
        ...         f() is dummy
        True


    Beware that :py
            ...     world.test.override.singleton(MyService, dummy)
            ...     # override twice MyService
            ...     world.test.override.singleton(MyService, dummy)
            ...     with world.test.clone():
            ...         f() is dummy
            False
            >>> with world.test.clone():
            ...     world.test.override.singleton(MyService, dummy)
            ...     with world.test.clone(keep_singletons=True):
            ...         f() is dummy
            True


        Beware that :py
            ...     world.test.override.singleton(MyService, dummy)
            ...     # override twice MyService
            ...     world.test.override.singleton(MyService, dummy)
            ...     with world.test.clone():
            ...         f() is dummy
            False
            >>> with world.test.copy():
            ...     world.test.override.singleton(MyService, dummy)
            ...     with world.test.clone(keep_singletons=True):
            ...         f() is dummy
            True


        Beware that :py
            ...     world.test.override.singleton(MyService, dummy)
            ...     # override twice MyService
            ...     world.test.override.singleton(MyService, dummy)
            ...     with world.test.clone():
            ...         f() is dummy
            False
            >>> with world.test.copy():
            ...     world.test.override.singleton(MyService, dummy)
            ...     with world.test.clone(keep_singletons=True):
            ...         f() is dummy
            True


        Beware that :py
        ...     world.test.override.singleton(MyService, dummy)
        ...     # override twice MyService
        ...     world.test.override.singleton(MyService, dummy)
        ...     with world.test.clone():
        ...         f() is dummy
        False
        >>> with world.test.copy():
        ...     world.test.override.singleton(MyService, dummy)
        ...     with world.test.clone(keep_singletons=True):
        ...         f() is dummy
        True


    Beware that :py
            ...     world.test.override.singleton(MyService, dummy)
            ...     # override twice MyService
            ...     world.test.override.singleton(MyService, dummy)
            ...     with world.test.clone():
            ...         f() is dummy
            False
            >>> with world.test.clone():
            ...     world.test.override.singleton(MyService, dummy)
            ...     with world.test.copy(keep_singletons=True):
            ...         f() is dummy
            True


        Beware that :py
            ...     world.test.override.singleton(MyService, dummy)
            ...     # override twice MyService
            ...     world.test.override.singleton(MyService, dummy)
            ...     with world.test.clone():
            ...         f() is dummy
            False
            >>> with world.test.copy():
            ...     world.test.override.singleton(MyService, dummy)
            ...     with world.test.clone(keep_singletons=True):
            ...         f() is dummy
            True


        Beware that :py
            ...     world.test.override.singleton(MyService, dummy)
            ...     # override twice MyService
            ...     world.test.override.singleton(MyService, dummy)
            ...     with world.test.clone():
            ...         f() is dummy
            False
            >>> with world.test.copy():
            ...     world.test.override.singleton(MyService, dummy)
            ...     with world.test.clone(keep_singletons=True):
            ...         f() is dummy
            True


        Beware that :py
        ...     world.test.override.singleton(MyService, dummy)
        ...     # override twice MyService
        ...     world.test.override.singleton(MyService, dummy)
        ...     with world.test.clone():
        ...         f() is dummy
        False
        >>> with world.test.clone():
        ...     world.test.override.singleton(MyService, dummy)
        ...     with world.test.clone(keep_singletons=True):
        ...         f() is dummy
        True


    Beware that :py
            ...     world.test.override.singleton(MyService, dummy)
            ...     # override twice MyService
            ...     world.test.override.singleton(MyService, dummy)
            ...     with world.test.clone():
            ...         f() is dummy
            False
            >>> with world.test.clone():
            ...     world.test.override.singleton(MyService, dummy)
            ...     with world.test.copy(keep_singletons=True):
            ...         f() is dummy
            True


        Beware that :py
            ...     world.test.override.singleton(MyService, dummy)
            ...     # override twice MyService
            ...     world.test.override.singleton(MyService, dummy)
            ...     with world.test.clone():
            ...         f() is dummy
            False
            >>> with world.test.copy():
            ...     world.test.override.singleton(MyService, dummy)
            ...     with world.test.clone(keep_singletons=True):
            ...         f() is dummy
            True


        Beware that :py
            ...     world.test.override.singleton(MyService, dummy)
            ...     # override twice MyService
            ...     world.test.override.singleton(MyService, dummy)
            ...     with world.test.clone():
            ...         f() is dummy
            False
            >>> with world.test.copy():
            ...     world.test.override.singleton(MyService, dummy)
            ...     with world.test.clone(keep_singletons=True):
            ...         f() is dummy
            True


        Beware that :py
        ...     world.test.override.singleton(MyService, dummy)
        ...     # override twice MyService
        ...     world.test.override.singleton(MyService, dummy)
        ...     with world.test.clone():
        ...         f() is dummy
        False
        >>> with world.test.clone():
        ...     world.test.override.singleton(MyService, dummy)
        ...     with world.test.clone(keep_singletons=True):
        ...         f() is dummy
        True


    Beware that :py
            ...     world.test.override.singleton(MyService, dummy)
            ...     # override twice MyService
            ...     world.test.override.singleton(MyService, dummy)
            ...     with world.test.clone():
            ...         f() is dummy
            False
            >>> with world.test.copy():
            ...     world.test.override.singleton(MyService, dummy)
            ...     with world.test.copy(keep_singletons=True):
            ...         f() is dummy
            True


        Beware that :py
            ...     world.test.override.singleton(MyService, dummy)
            ...     # override twice MyService
            ...     world.test.override.singleton(MyService, dummy)
            ...     with world.test.clone():
            ...         f() is dummy
            False
            >>> with world.test.copy():
            ...     world.test.override.singleton(MyService, dummy)
            ...     with world.test.clone(keep_singletons=True):
            ...         f() is dummy
            True


        Beware that :py
            ...     world.test.override.singleton(MyService, dummy)
            ...     # override twice MyService
            ...     world.test.override.singleton(MyService, dummy)
            ...     with world.test.clone():
            ...         f() is dummy
            False
            >>> with world.test.copy():
            ...     world.test.override.singleton(MyService, dummy)
            ...     with world.test.clone(keep_singletons=True):
            ...         f() is dummy
            True


        Beware that :py
        ...     world.test.override.singleton(MyService, dummy)
        ...     # override twice MyService
        ...     world.test.override.singleton(MyService, dummy)
        ...     with world.test.clone():
        ...         f() is dummy
        False
        >>> with world.test.clone():
        ...     world.test.override.singleton(MyService, dummy)
        ...     with world.test.clone(keep_singletons=True):
        ...         f() is dummy
        True


    Beware that :py
            ...     world.test.override.singleton(MyService, dummy)
            ...     # override twice MyService
            ...     world.test.override.singleton(MyService, dummy)
            ...     with world.test.clone():
            ...         f() is dummy
            False
            >>> with world.test.copy():
            ...     world.test.override.singleton(MyService, dummy)
            ...     with world.test.copy(keep_singletons=True):
            ...         f() is dummy
            True


        Beware that :py
            ...     world.test.override.singleton(MyService, dummy)
            ...     # override twice MyService
            ...     world.test.override.singleton(MyService, dummy)
            ...     with world.test.clone():
            ...         f() is dummy
            False
            >>> with world.test.copy():
            ...     world.test.override.singleton(MyService, dummy)
            ...     with world.test.clone(keep_singletons=True):
            ...         f() is dummy
            True


        Beware that :py
            ...     world.test.override.singleton(MyService, dummy)
            ...     # override twice MyService
            ...     world.test.override.singleton(MyService, dummy)
            ...     with world.test.clone():
            ...         f() is dummy
            False
            >>> with world.test.copy():
            ...     world.test.override.singleton(MyService, dummy)
            ...     with world.test.clone(keep_singletons=True):
            ...         f() is dummy
            True


        Beware that :py
        ...     world.test.override.singleton(MyService, dummy)
        ...     # override twice MyService
        ...     world.test.override.singleton(MyService, dummy)
        ...     with world.test.clone():
        ...         f() is dummy
        False
        >>> with world.test.clone():
        ...     world.test.override.singleton(MyService, dummy)
        ...     with world.test.clone(keep_singletons=True):
        ...         f() is dummy
        True


    Beware that :py
            ...     world.test.override.singleton(MyService, dummy)
            ...     # override twice MyService
            ...     world.test.override.singleton(MyService, dummy)
            ...     with world.test.clone():
            ...         f() is dummy
            False
            >>> with world.test.clone():
            ...     world.test.override.singleton(MyService, dummy)
            ...     with world.test.clone(keep_singletons=True):
            ...         f() is dummy
            True


        Beware that :py
            ...     world.test.override.singleton(MyService, dummy)
            ...     # override twice MyService
            ...     world.test.override.singleton(MyService, dummy)
            ...     with world.test.clone():
            ...         f() is dummy
            False
            >>> with world.test.copy():
            ...     world.test.override.singleton(MyService, dummy)
            ...     with world.test.copy(keep_singletons=True):
            ...         f() is dummy
            True


        Beware that :py
            ...     world.test.override.singleton(MyService, dummy)
            ...     # override twice MyService
            ...     world.test.override.singleton(MyService, dummy)
            ...     with world.test.clone():
            ...         f() is dummy
            False
            >>> with world.test.copy():
            ...     world.test.override.singleton(MyService, dummy)
            ...     with world.test.clone(keep_singletons=True):
            ...         f() is dummy
            True


        Beware that :py
        ...     world.test.override.singleton(MyService, dummy)
        ...     # override twice MyService
        ...     world.test.override.singleton(MyService, dummy)
        ...     with world.test.clone():
        ...         f() is dummy
        False
        >>> with world.test.clone():
        ...     world.test.override.singleton(MyService, dummy)
        ...     with world.test.clone(keep_singletons=True):
        ...         f() is dummy
        True


    Beware that :py
            ...     world.test.override.singleton(MyService, dummy)
            ...     # override twice MyService
            ...     world.test.override.singleton(MyService, dummy)
            ...     with world.test.clone():
            ...         f() is dummy
            False
            >>> with world.test.clone():
            ...     world.test.override.singleton(MyService, dummy)
            ...     with world.test.clone(keep_singletons=True):
            ...         f() is dummy
            True


        Beware that :py
            ...     world.test.override.singleton(MyService, dummy)
            ...     # override twice MyService
            ...     world.test.override.singleton(MyService, dummy)
            ...     with world.test.clone():
            ...         f() is dummy
            False
            >>> with world.test.copy():
            ...     world.test.override.singleton(MyService, dummy)
            ...     with world.test.copy(keep_singletons=True):
            ...         f() is dummy
            True


        Beware that :py
            ...     world.test.override.singleton(MyService, dummy)
            ...     # override twice MyService
            ...     world.test.override.singleton(MyService, dummy)
            ...     with world.test.clone():
            ...         f() is dummy
            False
            >>> with world.test.copy():
            ...     world.test.override.singleton(MyService, dummy)
            ...     with world.test.clone(keep_singletons=True):
            ...         f() is dummy
            True


        Beware that :py
        ...     world.test.override.singleton(MyService, dummy)
        ...     # override twice MyService
        ...     world.test.override.singleton(MyService, dummy)
        ...     with world.test.clone():
        ...         f() is dummy
        False
        >>> with world.test.clone():
        ...     world.test.override.singleton(MyService, dummy)
        ...     with world.test.clone(keep_singletons=True):
        ...         f() is dummy
        True


    Beware that :py
            ...     world.test.override.singleton(MyService, dummy)
            ...     # override twice MyService
            ...     world.test.override.singleton(MyService, dummy)
            ...     with world.test.clone():
            ...         f() is dummy
            False
            >>> with world.test.clone():
            ...     world.test.override.singleton(MyService, dummy)
            ...     with world.test.clone(keep_singletons=True):
            ...         f() is dummy
            True


        Beware that :py
            ...     world.test.override.singleton(MyService, dummy)
            ...     # override twice MyService
            ...     world.test.override.singleton(MyService, dummy)
            ...     with world.test.clone():
            ...         f() is dummy
            False
            >>> with world.test.copy():
            ...     world.test.override.singleton(MyService, dummy)
            ...     with world.test.clone(keep_singletons=True):
            ...         f() is dummy
            True


        Beware that :py
            ...     world.test.override.singleton(MyService, dummy)
            ...     # override twice MyService
            ...     world.test.override.singleton(MyService, dummy)
            ...     with world.test.clone():
            ...         f() is dummy
            False
            >>> with world.test.copy():
            ...     world.test.override.singleton(MyService, dummy)
            ...     with world.test.copy(keep_singletons=True):
            ...         f() is dummy
            True


        Beware that :py
        ...     world.test.override.singleton(MyService, dummy)
        ...     # override twice MyService
        ...     world.test.override.singleton(MyService, dummy)
        ...     with world.test.clone():
        ...         f() is dummy
        False
        >>> with world.test.clone():
        ...     world.test.override.singleton(MyService, dummy)
        ...     with world.test.clone(keep_singletons=True):
        ...         f() is dummy
        True


    Beware that :py
            ...     world.test.override.singleton(MyService, dummy)
            ...     # override twice MyService
            ...     world.test.override.singleton(MyService, dummy)
            ...     with world.test.clone():
            ...         f() is dummy
            False
            >>> with world.test.clone():
            ...     world.test.override.singleton(MyService, dummy)
            ...     with world.test.clone(keep_singletons=True):
            ...         f() is dummy
            True


        Beware that :py
            ...     world.test.override.singleton(MyService, dummy)
            ...     # override twice MyService
            ...     world.test.override.singleton(MyService, dummy)
            ...     with world.test.clone():
            ...         f() is dummy
            False
            >>> with world.test.copy():
            ...     world.test.override.singleton(MyService, dummy)
            ...     with world.test.clone(keep_singletons=True):
            ...         f() is dummy
            True


        Beware that :py
            ...     world.test.override.singleton(MyService, dummy)
            ...     # override twice MyService
            ...     world.test.override.singleton(MyService, dummy)
            ...     with world.test.clone():
            ...         f() is dummy
            False
            >>> with world.test.copy():
            ...     world.test.override.singleton(MyService, dummy)
            ...     with world.test.copy(keep_singletons=True):
            ...         f() is dummy
            True


        Beware that :py
        ...     world.test.override.singleton(MyService, dummy)
        ...     # override twice MyService
        ...     world.test.override.singleton(MyService, dummy)
        ...     with world.test.clone():
        ...         f() is dummy
        False
        >>> with world.test.clone():
        ...     world.test.override.singleton(MyService, dummy)
        ...     with world.test.clone(keep_singletons=True):
        ...         f() is dummy
        True


    Beware that :py
        ...     world.test.override.singleton(MyService, dummy)
        ...     # override twice MyService
        ...     world.test.override.singleton(MyService, dummy)
        ...     with world.test.clone():
        ...         f() is dummy
        False
        >>> with world.test.clone():
        ...     world.test.override.singleton(MyService, dummy)
        ...     with world.test.clone(keep_singletons=True):
        ...         f() is dummy
        True


    Beware that :py
        ...     world.test.override.singleton(MyService, dummy)
        ...     # override twice MyService
        ...     world.test.override.singleton(MyService, dummy)
        ...     with world.test.clone():
        ...         f() is dummy
        False
        >>> with world.test.copy():
        ...     world.test.override.singleton(MyService, dummy)
        ...     with world.test.clone(keep_singletons=True):
        ...         f() is dummy
        True


    Beware that :py
        ...     world.test.override.singleton(MyService, dummy)
        ...     # override twice MyService
        ...     world.test.override.singleton(MyService, dummy)
        ...     with world.test.clone():
        ...         f() is dummy
        False
        >>> with world.test.copy():
        ...     world.test.override.singleton(MyService, dummy)
        ...     with world.test.clone(keep_singletons=True):
        ...         f() is dummy
        True


    Beware that :py
    ...     world.test.override.singleton(MyService, dummy)
    ...     # override twice MyService
    ...     world.test.override.singleton(MyService, dummy)
    ...     with world.test.clone():
    ...         f() is dummy
    False
    >>> with world.test.clone():
    ...     world.test.override.singleton(MyService, dummy)
    ...     with world.test.clone(keep_singletons=True):
    ...         f() is dummy
    True


Beware that :py:func:`world.test.clone` will automatically :py:func:`.world.freeze`: no new dependencies
cannot be defined. After all you want to test your existing dependencies not create new ones.

.. doctest:: tutorial_test

    >>> with world.test.copy():
        ...     @injectable
        ...     class NewService:
        ...         pass
        Traceback (most recent call last):
          File "<stdin>", line 1, in ?
        FrozenWorldError

    To test new dependencies, you should use :py
    ...     @injectable
    ...     class NewService:
    ...         pass
    Traceback (most recent call last):
      File "<stdin>", line 1, in ?
    FrozenWorldError

To test new dependencies, you should use :py:func:`.world.test.new` instead:

.. doctest:: tutorial_test

    >>> with world.test.new():
    ...     @injectable
    ...     class NewService:
    ...         pass
    ...     world.get(NewService)
    <NewService ...>
    >>> world.get[NewService]()
    Traceback (most recent call last):
      File "<stdin>", line 1, in ?
    DependencyNotFoundError
