from __future__ import annotations

from typing import TypeVar

from typing_extensions import Annotated

from ._annotation import InjectAnnotation

__all__ = ["Inject"]

T = TypeVar("T")

# API.public
Inject = Annotated[T, InjectAnnotation()]
Inject.__doc__ = """
Annotation specifying that the type hint itself is the dependency:

.. doctest:: core_annotation_inject

    >>> from antidote import world, inject, Inject, injectable
    >>> @injectable
    ... class Database:
    ...     pass
    >>> @inject
    ... def load_db(db: Inject[Database]):
    ...     return db
    >>> load_db()
    <Database ...>

"""
