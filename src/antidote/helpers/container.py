from ..core import DependencyContainer
from ..providers import LazyCallProvider, ServiceProvider, TagProvider


def new_container() -> DependencyContainer:
    container = DependencyContainer()
    container.register_provider(ServiceProvider(container))
    container.register_provider(LazyCallProvider(container))
    container.register_provider(TagProvider(container))

    return container
