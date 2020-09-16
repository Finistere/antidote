from ._internal import API


@API.public
def is_compiled() -> bool:
    """
    Whether current Antidote implementations is the compiled (Cython) version or not
    """
    from ._internal.wrapper import compiled
    return compiled
