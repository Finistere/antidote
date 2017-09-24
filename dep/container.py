import inspect
import weakref
import wrapt
import re
import sys
from .exceptions import *
from .util import to_snake_case
from collections import UserDict

try:
    from collections import ChainMap
except ImportError:
    from chainmap import ChainMap


PY2 = sys.version_info[0] < 3


_register_arg_pattern = re.compile(
    r'register\s*\(([\w_]+?)(?:,.*)*\)\s*(?:$|;)'
)
_register_kwarg_pattern = re.compile(
    r'register\s*\((?:.*,)*\s*service=([\w_]+?)(?:,.*)*\)\s*(?:$|;)'
)


class ServicesDict(UserDict):
    def __setitem__(self, key, value):
        if key in self:
            raise DuplicateServiceError(key)
        super(ServicesDict, self).__setitem__(key, value)


class ServicesContainer:
    auto_wire = True

    def __init__(self):
        self.builder = ServiceBuilder(weakref.proxy(self))

        self._services_by_class = ServicesDict()
        self._services_by_id = ServicesDict()

        self._services = ChainMap(
            self._services_by_id,
            self._services_by_class,
        )
        self._services_instances = {}

    def __getitem__(self, item):
        try:
            return self._services_instances[item]
        except KeyError:
            try:
                service = self._services[item]
            except KeyError:
                raise UndefinedServiceError(item)
            else:
                if service.auto_wire:
                    instance = self.builder.build(service.obj,
                                                  args=tuple(),
                                                  kwargs={})
                else:
                    try:
                        instance = service.obj()
                    except Exception as e:
                        raise ServiceInstantiationError(e)

                self._services_instances[item] = instance
                return instance

    def __setitem__(self, key, value):
        self._services_instances[key] = value

    def register(self, service=None, id=None, auto_wire=True):
        if service and not id and not inspect.isclass(service):
            frame = inspect.currentframe()
            # May be none for other Python implementation
            if frame is not None:
                try:
                    id = self._guess_name_from_caller_code(
                        inspect.getframeinfo(frame.f_back).code_context
                    )
                except:
                    pass
                finally:
                    del frame

            if id is None:
                raise ValueError('name cannot be None')

        def _register(obj):
            if inspect.isclass(obj):
                service = Service(obj, auto_wire=auto_wire)
                if PY2:
                    class_name = obj.__name__
                    for key in [class_name, to_snake_case(class_name)]:
                        self._services_by_class[key] = service
                else:
                    self._services_by_class[obj] = service

                if id:
                    self._services_by_id[id] = service
            else:
                self._services_instances[id] = obj

            return obj

        if service:
            return _register(service)

        return _register

    def _guess_name_from_caller_code(self, code_context):
        caller_lines = ''.join([line.strip() for line in code_context])
        matches = []
        matches.extend(
            re.findall(_register_arg_pattern, caller_lines)
        )
        matches.extend(
            re.findall(_register_kwarg_pattern, caller_lines)
        )

        # Use only if no doubt
        if len(matches) == 1:
            return matches[0]

        return None

    def inject(self, func=None):
        @wrapt.decorator
        def _inject(wrapped, instance, args, kwargs):
            return self.builder.build(wrapped, args, kwargs)

        if func:
            return _inject(func)

        return _inject


class Service:
    def __init__(self, obj, auto_wire):
        self.obj = obj
        self.auto_wire = auto_wire


class ServiceBuilder:
    def __init__(self, container):
        self._container = container

    def build(self, obj, args, kwargs):
        f = obj.__init__ if inspect.isclass(obj) else obj
        new_args, new_kwargs = self._inject_services(f, args, kwargs)

        try:
            return obj(*new_args, **new_kwargs)
        except Exception as e:
            raise ServiceInstantiationError(e)

    if PY2:
        def _inject_services(self, f, args, kwargs):
            arg_spec = inspect.getargspec(f)
            kwargs = kwargs.copy()

            for name in arg_spec.args[len(args):]:
                if name not in kwargs:
                    try:
                        kwargs[name] = self._container[name]
                    except UndefinedServiceError:
                        pass
            
            return args, kwargs
    else:
        def _inject_services(self, f, args, kwargs):
            signature = inspect.signature(f)
            new_parameters = []

            for name, parameter in signature.parameters.items():
                if name == 'self':
                    continue

                try:
                    if parameter.annotation != parameter.empty:
                        parameter = parameter.replace(
                            default=self._container[parameter.annotation]
                        )
                except UndefinedServiceError:
                    pass
                finally:
                    new_parameters.append(parameter)

            signature = signature.replace(parameters=new_parameters)
            bound_arguments = signature.bind_partial(*args, **kwargs)
            bound_arguments.apply_defaults()

            return bound_arguments.args, bound_arguments.kwargs
