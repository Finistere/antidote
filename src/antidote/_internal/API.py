from typing import TypeVar

from typing_extensions import Annotated

T = TypeVar('T')


def public(x: T) -> T:
    """
    Objects marked with this decorator are considered to be in the public API.
    Breaking changes will be avoided and will be taken into account in the
    semantic versioning.
    """
    return x  # pragma: no cover


def deprecated(x: T) -> T:
    """
    Objects marked with this decorator are considered to be deprecated. Use the documented
    alternative if it exists, as this object will be removed in a future release.
    """
    return x  # pragma: no cover


def experimental(x: T) -> T:
    """
    Similar to public, they're part of the public API *BUT* they're not stable.
    As such there's a good chance they may be changed or removed in the next release. If
    you're relying on an experimental feature consider opening an issue with your use case
    to advocate its migration to public !
    """
    return x  # pragma: no cover


def private(x: T) -> T:
    """
    Only for internal use. They are NOT part of the public API, and as such may
    change without warning in later versions. If you rely on private APIs, please open
    an issue.
    """
    return x  # pragma: no cover


Deprecated = Annotated[T, "deprecated argument"]
