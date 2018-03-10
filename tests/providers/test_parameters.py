import pytest

from antidote.exceptions import DependencyNotProvidableError
from antidote.providers.parameters import ParameterProvider, rgetitem


def test_rgetitem():
    data = {
        'data': {
            'key1': object()
        },
        'something': object()
    }

    assert data['something'] is rgetitem(data, ['something'])
    assert data['data']['key1'] is rgetitem(data, ['data', 'key1'])

    with pytest.raises(KeyError):
        rgetitem(data, ['data', 'nothing'])


def test_register():
    provider = ParameterProvider()
    conf = {
        'service': object(),
        'another': 1,
        'simple': 'yes',
        'recursive': {
            'test': object()
        },
        1: 1
    }

    def conf_parser(dependency_id):
        if isinstance(dependency_id, str):
            if dependency_id.startswith('conf:'):
                return dependency_id[5:].split('.')

    provider.register(conf_parser, conf)

    def provide(e):
        return provider.__antidote_provide__(e).instance

    with pytest.raises(DependencyNotProvidableError):
        provide('service')

    with pytest.raises(DependencyNotProvidableError):
        provide(1)

    assert conf['service'] is provide('conf:service')
    assert 1 == provide('conf:another')
    assert conf['recursive']['test'] is provide('conf:recursive.test')

    with pytest.raises(DependencyNotProvidableError):
        provide('conf:nothing')

    with pytest.raises(DependencyNotProvidableError):
        provide('conf:simple.yes.nothing')

    with pytest.raises(DependencyNotProvidableError):
        provide('conf:recursive.test.nothing')
