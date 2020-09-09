def new_container():
    from ..core import DependencyContainer
    from ..providers import LazyCallProvider, FactoryProvider, TagProvider, \
        IndirectProvider

    container = DependencyContainer()
    container.register_provider(FactoryProvider())
    container.register_provider(LazyCallProvider())
    container.register_provider(TagProvider())
    container.register_provider(IndirectProvider())

    return container
