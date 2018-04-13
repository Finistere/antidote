import pytest

from antidote import DependencyNotProvidableError
from antidote.providers import ParameterProvider
from antidote.utils import rgetitem


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

    def conf_parser(parameters, dependency_id):
        if isinstance(dependency_id, str):
            if dependency_id.startswith('conf:'):
                return rgetitem(parameters, dependency_id[5:].split('.'))

        raise LookupError(dependency_id)

    provider.register(conf, conf_parser)

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

    assert repr(conf) in repr(provider)
