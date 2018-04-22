import pytest

from antidote import DependencyNotProvidableError
from antidote.providers.parameters import ParameterProvider, Dependency
from functools import reduce
from operator import getitem


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

    def conf_parser(params, dependency_id):
        if isinstance(dependency_id, str):
            if dependency_id.startswith('conf:'):
                try:
                    return reduce(getitem, dependency_id[5:].split('.'),
                                  params)
                except TypeError as e:
                    raise LookupError(dependency_id) from e

        raise LookupError(dependency_id)

    provider.register(conf, conf_parser)

    def provide(e):
        return provider.__antidote_provide__(Dependency(e)).item

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
