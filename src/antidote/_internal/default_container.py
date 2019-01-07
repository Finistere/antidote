from ..core import DependencyContainer


def get_default_container() -> DependencyContainer:
    import antidote
    return antidote.world
