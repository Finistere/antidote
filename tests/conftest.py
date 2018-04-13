import sys

import os
import pytest

PY3 = sys.version_info[0] >= 3

if os.environ.get('MOCK_ATTRS'):
    @pytest.fixture(autouse=True, scope="function")
    def hide_attr(monkeypatch):
        """
        Hide attrs from Antidote as it is currently a dependency of pytest.
        """
        # Store original __import__
        builtin_import = __import__

        def _import(name, *args):
            if name == 'attr':
                raise ImportError(name)
            return builtin_import(name, *args)

        if PY3:
            builtins_module = 'builtins'
        else:
            builtins_module = '__builtin__'

        monkeypatch.setattr('{}.__import__'.format(builtins_module), _import)
