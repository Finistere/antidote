Changelog
=========


0.4.0-dev
---------

Breaking changes
^^^^^^^^^^^^^^^^

- `Dependency` does not take additional arguments anymore, for custom dependencies
  `Build`, `Tagged` must be used.
- Custom providers must inherit `Provider`.
- `register_parameters()` has been replaced by a more general function, `getter()`.
  See the documentation to imitate its functionality.
- Rename arguments `cls` to `class_` in `provider()`, `wire()`, `register()`.

Features
^^^^^^^^

- Dependencies can be tagged at registration. Those can then be retrieved as
  a dependency. This allows one to extend an app by registering a service in
  special way just by adding a tag.
- Type hints usage can now be finely controlled or disabled with `use_type_hints`.
- Add `getter()` to support custom string dependencies.

Changes
^^^^^^^

- Add :code:`DependencyManager.provide` method for easier manipulation in the
  shell.

Bug fixes
^^^^^^^^^

- When :code:`DependencyManager.factory` was applied on a class it would return
  an instance of it and not the class itself.


0.3.0 (2018-04-29)
------------------

Initial release
