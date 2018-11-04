from configparser import RawConfigParser
from operator import getitem

import pytest

from antidote import DependencyManager, DependencyNotFoundError


def test_parameters():
    manager = DependencyManager()
    container = manager.container

    manager.register_parameters({'test1': 'some value'}, getter=getitem)
    assert 'some value' == container['test1']

    manager.register_parameters({'test2': 'another value'}, getter=getitem,
                                prefix='conf:')
    assert 'another value' == container['conf:test2']

    manager.register_parameters({'test3': {'nested': 'yes'}}, getter=getitem,
                                split='.')
    assert 'yes' == container['test3.nested']

    manager.register_parameters({'param': '1', 'paramb': {'test': 2}},
                                getter=getitem, prefix='params:', split='.')

    assert '1' == container['params:param']
    assert 2 == container['params:paramb.test']

    with pytest.raises(DependencyNotFoundError):
        container[object()]

    with pytest.raises(DependencyNotFoundError):
        container['test3.nested.yes']


def test_register_parameters_custom_getter():
    manager = DependencyManager()
    container = manager.container

    @manager.register_parameters({'a': {'b': {'c': 99}}})
    def parser(obj, item):
        from functools import reduce
        if isinstance(item, str):
            return reduce(getitem, list(item), obj)

        raise LookupError(item)

    assert 99 == container['abc']

    # Does not fail with missing dependency
    with pytest.raises(DependencyNotFoundError):
        container[object()]


def test_invalid_arguments():
    manager = DependencyManager()

    with pytest.raises(ValueError):
        manager.register_parameters(object(), getter=object())

    with pytest.raises(ValueError):
        manager.register_parameters(object(), prefix=object())

    with pytest.raises(ValueError):
        manager.register_parameters(object(), split=object())


def test_parameters_with_configparser():
    manager = DependencyManager()
    container = manager.container

    cfg = RawConfigParser()
    cfg.add_section('test')
    cfg.set('test', 'param', '100')

    manager.register_parameters(cfg, getter=getitem, split='.')

    assert '100' == container['test.param']

    with pytest.raises(DependencyNotFoundError):
        container['section.option']

    with pytest.raises(DependencyNotFoundError):
        container['test.option']

    with pytest.raises(DependencyNotFoundError):
        container['test.param.test']
