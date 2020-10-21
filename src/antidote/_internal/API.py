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
    Similar to public, they're part of the public API. However it's not really stable.
    Hence there's a good chance they may be changed or removed in the next release. If
    you're relying on a experimental feature consider opening an issue with your use case
    to advocate its migration to public !
    """
    return x


def private(x: T) -> T:
    """
    Only for internal use. They're are NOT part of the public API, and as such may
    change without warning in later versions. If you rely on private APIs, please open
    an issue.
    """
    return x
