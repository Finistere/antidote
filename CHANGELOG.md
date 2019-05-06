Changelog
=========


0.6.0 (2019-05-06)
------------------
  
### Features

- Add `@implements` to define service implementing an interface. 
- Add `IndirectProvider()` which supports `@implements`.
- Add `DependencyContainer.safe_provide()` which does the same as 
  `DependencyContainer.provide()` except that it raises an error if
  the dependency cannot be found instead of returning None.


### Breaking changes

- `DependencyContainer.provide()` returns a `DependencyInstance` not the 
  instance itself anymore.
- Rename `LazyConfigurationMeta` to `LazyConstantsMeta`.
- `LazyConfigurationMeta` default method is `get()`.
- `ServiceProvider` renamed to `FactoryProvider` and reworked 
  `ServiceProvider.register()` with is split into `register_factory()`,
  `register_class`, `register_providable_factory`.


### Changes

- Moved `is_compiled` to `antidote.utils`.
- Add better type hints.


0.5.1 (2019-04-27)
------------------
  
### Features

- Add `is_compiled()` to check whether the current version is compiled or pure 
  python.


0.5.0 (2019-04-27)
------------------

### Breaking changes

- `@resource` has been removed an replaced by `LazyConfigurationMeta` to handle 
  configuration. 
  
### Features

- Add `LazyMethodCall` and `LazyCall` to support output of functions as dependencies.

### Changes

- Add better type hints for helper decorators.


0.4.0 (2019-02-03)
------------------

A lot of internals have changed, but it can roughly be resumed as the following:

### Breaking changes

- The `DependencyManager` does not exist anymore and has been replaced by 
  multiple helpers which accepts a `container` argument. By default the global
  container of Antidote is used. Thus one can easily replace 
  `from antidote import antidote` to `import antidote` to adapt existing code.
- The global container of Antidote, previously named `container`, has been 
  renamed `world`.
- `Dependency` does not take additional arguments anymore, for custom 
  dependencies `Build`, `Tagged` must be used instead.
- Custom providers must inherit `Provider`.
- `register_parameters()` has been replaced by a more general function, 
  `resource()`. See the documentation to imitate its functionality.
- `factory()` is more strict. Subclasses are not handled anymore, one should
  use `register()` with its `factory` argument instead.

### Features

- Dependencies can be tagged at registration. Those can then be retrieved as
  a dependency. This allows one to extend an app by registering a service in
  special way just by adding a tag.
- Type hints usage can now be finely controlled or disabled with `use_type_hints`.
- Add `resource()` to support custom resources, such as configuration.
- Dependency providers are more strict for more maintainable code.
- Use of Cython for better injection performance.


0.3.0 (2018-04-29)
------------------

Initial release
