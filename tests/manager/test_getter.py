import functools
import textwrap

import pytest

from antidote import DependencyManager


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


@pytest.mark.parametrize(
    'mk_getter',
    [mk_simple_getter, mk_complex_getter]
)
def test_simple_getter(mk_getter):
    manager = DependencyManager()

    data = {
        'test': object(),
        'test3': object(),
        'http:test': object(),
        'conf3test': object()
    }
    mk_getter = functools.partial(mk_getter, data=data)

    manager.getter()(mk_getter('conf'))
    assert data['test'] == manager.container['conf:test']

    manager.getter(omit_namespace=False)(mk_getter('http'))
    assert data['http:test'] == manager.container['http:test']

    manager.getter(namespace='conf2:', omit_namespace=True)(mk_getter('conf'))
    assert data['test3'] == manager.container['conf2:test3']

    manager.getter(namespace='conf3', omit_namespace=False)(mk_getter('conf'))
    assert data['conf3test'] == manager.container['conf3test']
