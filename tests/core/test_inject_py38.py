from typing import Dict, Tuple

from antidote import inject, world
from tests.utils import Obj

x = Obj()


def test_positional_arguments() -> None:
    with world.test.empty() as overrides:
        overrides[x] = x

        @inject(dict(a=x))
        def f1(
            x: object = 0, /, a: object = None, **kwargs: object  # pyright: ignore
        ) -> Tuple[object, object, Dict[str, object]]:
            return x, a, kwargs

        assert f1() == (0, x, {})
        assert f1(1) == (1, x, {})
        assert f1(1, 2) == (1, 2, {})
        assert f1(b=2) == (0, x, dict(b=2))
        assert f1(1, b=2) == (1, x, dict(b=2))
