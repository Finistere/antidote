Changelog
=========


0.4.0-dev
---------

### Breaking changes

- The `DependencyManager` does not exist anymore and has been replaced by 
  multiple helpers which accepts a `container` argument. By default the global
  container of Antidote is used. Thus one can easily replace 
  `from antidote import antidote` to `import antidote` to adapt existing code.
- The global container of Antidote, previously named `container`, has been 
  renamed `global_container`.
- `Dependency` does not take additional arguments anymore, for custom 
  dependencies `Build`, `Tagged` must be used instead.
- Custom providers must inherit `Provider`.
- `register_parameters()` has been replaced by a more general function, 
  `resource()`. See the documentation to imitate its functionality.
- In `provider()`, `wire()`, `register()`, the argument `cls` has  been renamed
  `class_`.

### Features

- Dependencies can be tagged at registration. Those can then be retrieved as
  a dependency. This allows one to extend an app by registering a service in
  special way just by adding a tag.
- Type hints usage can now be finely controlled or disabled with `use_type_hints`.
- Add `getter()` to support custom string dependencies.

### Changes

- Add `DependencyManager.provide` method for easier manipulation in the
  shell.

### Bug fixes

- When `DependencyManager.factory` was applied on a class it would return
  an instance of it and not the class itself.


0.3.0 (2018-04-29)
------------------

Initial release
