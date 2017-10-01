from .container import ServiceManager

manager = ServiceManager()

inject = manager.inject
provider = manager.inject
register = manager.inject
