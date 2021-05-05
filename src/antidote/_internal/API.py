from typing import TypeVar

T = TypeVar('T')


def public(x: T) -> T:
    """
    Objects marked with this decorator are considered to be in the public API.
    Breaking changes will be avoided and will be taken into account in the
    semantic versioning.
    """
    return x


def private(x: T) -> T:
    """
    Only for internal use. They're are NOT part of the public API, and as such may
    change without warning in later versions. If you rely on private APIs, please open
    an issue.
    """
    return x
