from typing import Union


def info(dependency, *, recursive: Union[bool, int] = True) -> str:
    from .._internal.state import get_container
    from .._internal.utils.debug import tree_debug_info
    if isinstance(recursive, bool):
        recursive = 1 << 31 if recursive else 0

    return tree_debug_info(get_container(),
                           dependency,
                           max_depth=recursive)
