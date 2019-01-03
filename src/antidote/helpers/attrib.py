from typing import Any, get_type_hints

from ..core import DependencyContainer
from .._internal.default_container import get_default_container


def attrib(dependency: Any = None,
           use_name: bool = None,
           container: DependencyContainer = None,
           **attr_kwargs):
    """Injects a dependency with attributes defined with attrs package.

    Args:
        dependency: Dependency to inject. Defaults to the type hint.
        use_name: If True, use the attribute name as the dependency,
            overriding any annotations.
        container: :py:class:~.core.base.DependencyContainer` to which the
            dependency should be attached. Defaults to the global core if
            it is defined.
        **attr_kwargs: Keyword arguments passed on to attr.ib()

    Returns:
        object: attr.Attribute with a attr.Factory.

    """
    container = container or get_default_container()

    try:
        import attr
    except ImportError:
        raise RuntimeError("attrs package must be installed.")

    def factory(instance):
        nonlocal dependency

        if dependency is None:
            cls = instance.__class__
            type_hints = get_type_hints(cls) or {}

            for attribute in attr.fields(cls):
                # Dirty way to find the attrib annotation.
                # Maybe attr will eventually provide the annotation ?
                if isinstance(attribute.default, attr.Factory) \
                        and attribute.default.factory is factory:
                    try:
                        dependency = type_hints[attribute.name]
                    except KeyError:
                        if use_name:
                            dependency = attribute.name
                            break
                    else:
                        break
            else:
                raise RuntimeError(
                    "No dependency could be detected. Please specify "
                    "the parameter `dependency` or `use_name=True`."
                    "Annotations may also be used."
                )

        return container[dependency]

    return attr.ib(default=attr.Factory(factory, takes_self=True), **attr_kwargs)
