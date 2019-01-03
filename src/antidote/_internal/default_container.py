from ..core import DependencyContainer


def get_default_container() -> DependencyContainer:
    import antidote
    return antidote.world


def set_default_container(container: DependencyContainer):
    import antidote
    antidote.world = container
