from ..core import DependencyContainer
from ..providers import LazyCallProvider, FactoryProvider, TagProvider, IndirectProvider


def new_container() -> DependencyContainer:
    container = DependencyContainer()
    container.register_provider(FactoryProvider(container))
    container.register_provider(LazyCallProvider(container))
    container.register_provider(TagProvider(container))
    container.register_provider(IndirectProvider(container))

    return container
