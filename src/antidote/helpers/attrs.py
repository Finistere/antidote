from typing import Any, get_type_hints

from ..container import DependencyContainer
from .._internal.global_container import get_global_container


def attrib(dependency_id: Any = None,
           use_name: bool = None,
           container: DependencyContainer = None,
           **attr_kwargs):
    """Injects a dependency with attributes defined with attrs package.

    Args:
        dependency_id: Id of the dependency to inject. Defaults to the
            annotation.
        use_name: If True, use the attribute name as the dependency id
            overriding any annotations.
        container: :py:class:~.container.base.DependencyContainer` to which the
            dependency should be attached. Defaults to the global container if
            it is defined.
        **attr_kwargs: Keyword arguments passed on to attr.ib()

    Returns:
        object: attr.Attribute with a attr.Factory.

    """
    container = container or get_global_container()

    try:
        import attr
    except ImportError:
        raise RuntimeError("attrs package must be installed.")

    def factory(instance):
        nonlocal dependency_id

        if dependency_id is None:
            cls = instance.__class__
            type_hints = get_type_hints(cls) or {}

            for attribute in attr.fields(cls):
                # Dirty way to find the attrib annotation.
                # Maybe attr will eventually provide the annotation ?
                if isinstance(attribute.default, attr.Factory) \
                        and attribute.default.factory is factory:
                    try:
                        dependency_id = type_hints[attribute.name]
                    except KeyError:
                        if use_name:
                            dependency_id = attribute.name
                            break
                    else:
                        break
            else:
                raise ValueError(
                    "No dependency could be detected. Please specify "
                    "the parameter `dependency_id` or `use_name=True`."
                    "Annotations may also be used."
                )

        return container[dependency_id]

    return attr.ib(default=attr.Factory(factory, takes_self=True), **attr_kwargs)
