import functools
import textwrap

import pytest

from antidote import resource
from antidote.core import DependencyContainer
from antidote.providers import ResourceProvider, ServiceProvider


@pytest.fixture()
def container():
    c = DependencyContainer()
    c.register_provider(ResourceProvider(container=c))
    c.register_provider(ServiceProvider(container=c))

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
    getter_ = functools.partial(resource, container=container)

    data = {
        'test': object(),
        'test3': object(),
        'http:test': object(),
        'conf3:test': object()
    }
    mk_getter = functools.partial(mk_getter, data=data)

    getter_()(mk_getter('conf'))
    assert data['test'] == container['conf:test']
