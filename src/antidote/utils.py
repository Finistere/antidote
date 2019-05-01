def is_compiled() -> bool:
    from ._internal.wrapper import compiled
    return compiled
