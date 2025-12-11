"""Service registry for lazy-loading and dependency injection."""

import logging
from typing import Dict, Type, Any, Optional, Callable
from functools import wraps

logger = logging.getLogger(__name__)


class ServiceRegistry:
    """
    Central registry for managing service instances with lazy loading.
    
    This implements the Service Locator pattern with dependency injection
    to reduce memory footprint and startup time.
    """
    
    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._factories: Dict[str, Callable] = {}
        self._singletons: Dict[str, Any] = {}
        
    def register_factory(self, name: str, factory: Callable, singleton: bool = True):
        """
        Register a factory function for a service.
        
        Args:
            name: Service identifier
            factory: Function that creates the service instance
            singleton: If True, only one instance is created and reused
        """
        self._factories[name] = factory
        if singleton:
            logger.debug(f"Registered singleton factory for service: {name}")
        else:
            logger.debug(f"Registered transient factory for service: {name}")
    
    def register_instance(self, name: str, instance: Any):
        """
        Register an existing service instance.
        
        Args:
            name: Service identifier
            instance: Service instance
        """
        self._singletons[name] = instance
        logger.debug(f"Registered service instance: {name}")
    
    def get(self, name: str, **kwargs) -> Any:
        """
        Get a service instance by name.
        
        Args:
            name: Service identifier
            **kwargs: Additional arguments for factory
            
        Returns:
            Service instance
            
        Raises:
            KeyError: If service not registered
        """
        # Check if singleton exists
        if name in self._singletons:
            return self._singletons[name]
        
        # Check if factory exists
        if name not in self._factories:
            raise KeyError(f"Service '{name}' not registered")
        
        # Create new instance
        logger.debug(f"Creating service instance: {name}")
        instance = self._factories[name](**kwargs)
        
        # Cache as singleton if it's a singleton factory
        if name in self._factories:
            self._singletons[name] = instance
        
        return instance
    
    def has(self, name: str) -> bool:
        """Check if a service is registered."""
        return name in self._factories or name in self._singletons
    
    def clear(self):
        """Clear all cached service instances."""
        self._singletons.clear()
        logger.debug("Cleared all service instances")
    
    def unregister(self, name: str):
        """Remove a service from the registry."""
        self._factories.pop(name, None)
        self._singletons.pop(name, None)
        logger.debug(f"Unregistered service: {name}")


# Global service registry instance
_registry = ServiceRegistry()


def get_service(name: str, **kwargs) -> Any:
    """
    Get a service from the global registry.
    
    Args:
        name: Service identifier
        **kwargs: Additional arguments for factory
        
    Returns:
        Service instance
    """
    return _registry.get(name, **kwargs)


def register_service(name: str, factory: Optional[Callable] = None, 
                     singleton: bool = True, instance: Any = None):
    """
    Register a service with the global registry.
    
    Can be used as a decorator or called directly.
    
    Args:
        name: Service identifier
        factory: Factory function (if used as function)
        singleton: Whether to cache the instance
        instance: Pre-created instance to register
        
    Example:
        @register_service("my_service")
        class MyService:
            pass
            
        register_service("config", instance=config_obj)
    """
    if instance is not None:
        _registry.register_instance(name, instance)
        return instance
    
    def decorator(cls_or_func):
        if factory is not None:
            _registry.register_factory(name, factory, singleton)
        else:
            _registry.register_factory(name, cls_or_func, singleton)
        return cls_or_func
    
    if factory is not None:
        return decorator(factory)
    
    return decorator


def inject(*service_names: str):
    """
    Decorator to inject services as function arguments.
    
    Args:
        *service_names: Names of services to inject
        
    Example:
        @inject("config", "logger")
        def my_function(data, config=None, logger=None):
            logger.info(config.value)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Inject services that aren't already provided
            for name in service_names:
                if name not in kwargs:
                    kwargs[name] = get_service(name)
            return func(*args, **kwargs)
        return wrapper
    return decorator


def get_registry() -> ServiceRegistry:
    """Get the global service registry instance."""
    return _registry
