from __future__ import annotations

from typing import TypeVar

from typing_extensions import Annotated

from ._inject import InjectMeDependency

__all__ = ["InjectMe"]

T = TypeVar("T")

# API.public
InjectMe = Annotated[T, InjectMeDependency(args=(), kwargs={})]
InjectMe.__doc__ = """
Annotation specifying that the type hint itself is the dependency:

.. doctest:: core_annotation_inject

    >>> from antidote import world, inject, InjectMe, injectable
    >>> @injectable
    ... class Database:
    ...     pass
    >>> @inject
    ... def load_db(db: InjectMe[Database]):
    ...     return db
    >>> load_db()
    <Database ...>

"""
