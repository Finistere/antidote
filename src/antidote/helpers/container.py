from ..core import DependencyContainer
from ..providers import ResourceProvider, ServiceProvider, TagProvider


def new_container() -> DependencyContainer:
    container = DependencyContainer()
    container.register_provider(ServiceProvider(container))
    container.register_provider(ResourceProvider(container))
    container.register_provider(TagProvider(container))

    return container
