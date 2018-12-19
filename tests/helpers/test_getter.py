import functools
import textwrap

import pytest

from antidote import (DependencyContainer, GetterProvider)
from antidote.helpers import getter


@pytest.fixture()
def container():
    c = DependencyContainer()
    c.register_provider(GetterProvider())

    return c


def mk_simple_getter(name, data):
    namespace = {'data': data}
    code = textwrap.dedent("""
        def {name}(key):
            return data[key]
    """).format(**locals())
    exec(code, namespace)

    return namespace[name]


def mk_complex_getter(name, data):
    namespace = {'data': data}
    code = textwrap.dedent("""
        class {name}:
            def __call__(self, key):
                return data[key]
    """).format(**locals())
    exec(code, namespace)

    return namespace[name]


@pytest.fixture(params=[mk_simple_getter, mk_complex_getter],
                ids=['function', 'class'])
def mk_getter(request):
    return request.param


def test_namespace(mk_getter, container):
    getter_ = functools.partial(getter, container=container)

    data = {
        'test': object(),
        'test3': object(),
        'http:test': object(),
        'conf3test': object()
    }
    mk_getter = functools.partial(mk_getter, data=data)

    getter_()(mk_getter('conf'))
    assert data['test'] == container['conf:test']

    getter_(omit_namespace=False)(mk_getter('http'))
    assert data['http:test'] == container['http:test']

    getter_(namespace='conf2:', omit_namespace=True)(mk_getter('conf'))
    assert data['test3'] == container['conf2:test3']

    getter_(namespace='conf3', omit_namespace=False)(mk_getter('conf'))
    assert data['conf3test'] == container['conf3test']
