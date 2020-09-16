from typing import TypeVar

T = TypeVar('T')


def public(x: T) -> T:
    """
    Objects marked with this decorator are considered to be in the public API.
    Breaking changes will be avoided and will be taken into account in the
    semantic versioning.
    """
    return x


def experimental(x: T) -> T:
    """
    Similar to public, they're part of the public API. However it's not really stable
    or may simply be removed in the next release.
    """
    return x


def public_for_tests(x: T) -> T:
    """
    Similar to public, they're part of the public API. However they're only meant to
    be used in tests.
    """
    return x


def private(x: T) -> T:
    """
    Only for internal use. They're are NOT part of the public API, and as such may
    change without warning in later versions. If you need access to private APIs,
    please submit an issue.
    """
    return x
