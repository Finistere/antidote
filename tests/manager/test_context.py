import pytest

from antidote import (DependencyContainer, DependencyInjector,
                      DependencyManager, DependencyNotFoundError)


def test_context():
    manager = DependencyManager()
    manager.container['param'] = 1

    with manager.context(include=[]):
        with pytest.raises(DependencyNotFoundError):
            manager.container['param']

        manager.container[DependencyInjector]
        manager.container[DependencyContainer]

    with manager.context(include=['param']):
        assert 1 == manager.container['param']

        manager.container[DependencyInjector]
        manager.container[DependencyContainer]

    with manager.context(exclude=['param']):
        with pytest.raises(DependencyNotFoundError):
            manager.container['param']

        manager.container[DependencyInjector]
        manager.container[DependencyContainer]

    with manager.context(missing=['param']):
        with pytest.raises(DependencyNotFoundError):
            manager.container['param']

        manager.container[DependencyInjector]
        manager.container[DependencyContainer]

    with manager.context(dependencies={'param': 2}):
        assert 2 == manager.container['param']

        manager.container[DependencyInjector]
        manager.container[DependencyContainer]
