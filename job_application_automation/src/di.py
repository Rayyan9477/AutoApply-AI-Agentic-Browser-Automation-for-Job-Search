"""
Dependency Injection Container for the Job Application Automation system.
This module provides a centralized way to manage and inject dependencies.
"""

from typing import Any, Dict, Type, TypeVar, Optional, Callable
from functools import lru_cache
import logging
from pathlib import Path

# Type variable for dependency injection
T = TypeVar('T')

class DIContainer:
    """
    Simple dependency injection container that manages the creation and lifecycle
    of application components.
    """
    
    def __init__(self):
        """Initialize the container with default bindings."""
        self._bindings: Dict[Type, Callable[..., Any]] = {}
        self._instances: Dict[Type, Any] = {}
        
    def bind(self, interface: Type[T], implementation: Callable[..., T], *, singleton: bool = True) -> None:
        """
        Bind an interface to an implementation.
        
        Args:
            interface: The interface (usually an abstract class or protocol) to bind
            implementation: A callable that returns an instance of the interface
            singleton: If True, the same instance will be returned on subsequent resolutions
        """
        self._bindings[interface] = (implementation, singleton)
    
    def instance(self, interface: Type[T], instance: T) -> None:
        """
        Bind an interface to a specific instance.
        
        Args:
            interface: The interface to bind
            instance: The instance to bind to the interface
        """
        self._instances[interface] = instance
    
    def resolve(self, interface: Type[T]) -> T:
        """
        Resolve an instance of the specified interface.
        
        Args:
            interface: The interface to resolve
            
        Returns:
            An instance of the requested interface
            
        Raises:
            ValueError: If the interface is not bound
        """
        # Check if we already have an instance
        if interface in self._instances:
            return self._instances[interface]
            
        # Check if we have a binding
        if interface in self._bindings:
            implementation, is_singleton = self._bindings[interface]
            instance = implementation()
            
            if is_singleton:
                self._instances[interface] = instance
                
            return instance
            
        # Check if the interface is concrete and can be instantiated directly
        try:
            return interface()
        except (TypeError, ValueError) as e:
            raise ValueError(f"No binding found for {interface.__name__}: {str(e)}")
    
    def __call__(self, interface: Type[T]) -> T:
        """Alias for resolve() to support decorator syntax."""
        return self.resolve(interface)


# Global container instance
container = DIContainer()


def injectable(singleton: bool = True):
    """
    Decorator to mark a class as injectable.
    
    Args:
        singleton: If True, the same instance will be returned on subsequent resolutions
    """
    def decorator(cls):
        container.bind(cls, cls, singleton=singleton)
        return cls
    return decorator


def inject(interface: Type[T] = None, **kwargs):
    """
    Decorator or function to resolve dependencies.
    
    Can be used as:
        @inject
        def my_func(dep: Interface = inject(Interface)): ...
        
    Or:
        @inject(Interface1, Interface2)
        def my_func(dep1, dep2): ...
        
    Args:
        interface: The interface to resolve (when used as a parameter default)
        **kwargs: Additional keyword arguments for configuration
    """
    # Handle the case when used as a decorator with parameters
    if interface is not None and callable(interface):
        # Called as @inject without parameters
        return _inject_decorator(interface)
    
    # Called as @inject() or inject(Interface)
    def decorator(f):
        return _inject_decorator(f, interface, **kwargs)
    
    return decorator

def _inject_decorator(f, interface=None, **kwargs):
    """Helper function to handle the actual injection logic."""
    import inspect
    from functools import wraps
    
    sig = inspect.signature(f)
    
    @wraps(f)
    def wrapper(*args, **kw):
        # Get the bound arguments
        bound_args = sig.bind_partial(*args, **kw)
        
        # Process parameters with inject() default
        for name, param in sig.parameters.items():
            if name not in bound_args.arguments and hasattr(param.default, '__inject__'):
                # This parameter has an inject() default
                bound_args.arguments[name] = container.resolve(param.default.interface)
        
        # If a single interface was provided, inject it as the first argument
        if interface is not None and not args and not kw:
            return f(container.resolve(interface), **kwargs)
            
        return f(*bound_args.args, **bound_args.kwargs)
    
    # Mark the wrapper as injectable for testing
    wrapper.__wrapped__ = f
    return wrapper

# Add a marker to injectable parameters
class _InjectedParameter:
    def __init__(self, interface):
        self.interface = interface
        self.__inject__ = True

def inject_param(interface: Type[T]) -> T:
    """Mark a parameter for injection."""
    return _InjectedParameter(interface)


def configure_container(config: dict) -> None:
    """
    Configure the DI container with application services.
    
    Args:
        config: Application configuration object or dictionary
    """
    from job_application_automation.config.config import ApplicationConfig, get_config
    
    # Import services
    from job_application_automation.src.utils.browser_automation import JobSearchBrowser
    from job_application_automation.src.utils.web_scraping import JobDetailsScraper
    from job_application_automation.src.job_sources.linkedin_integration import LinkedInIntegration
    from job_application_automation.src.resume_cover_letter_generator import ResumeGenerator
    from job_application_automation.src.application_tracker import ApplicationTracker
    from job_application_automation.src.ats_integration import ATSIntegrationManager
    
    # Bind configuration
    if not isinstance(config, ApplicationConfig):
        config = get_config()  # Get the default config if not provided
    container.bind(ApplicationConfig, lambda: config, singleton=True)
    
    # Bind core services
    container.bind(
        JobSearchBrowser,
        lambda: JobSearchBrowser(config.browser),
        singleton=False
    )
    
    container.bind(
        JobDetailsScraper,
        lambda: JobDetailsScraper(config.crawl),
        singleton=True
    )
    
    container.bind(
        LinkedInIntegration,
        lambda: LinkedInIntegration(config.linkedin),
        singleton=True
    )
    
    container.bind(
        ResumeGenerator,
        lambda: ResumeGenerator(config.llm),
        singleton=True
    )
    
    container.bind(ApplicationTracker, ApplicationTracker, singleton=True)
    
    ats_manager = ATSIntegrationManager(config.llm)
    ats_manager.load_state()
    container.instance(ATSIntegrationManager, ats_manager)
    
    # Ensure data directories exist
    data_dir = Path(config.data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    for sub in ["generated_cover_letters", "ats_reports"]:
        (data_dir / sub).mkdir(exist_ok=True)
    
    # Configure logging
    log_dir = Path(config.logging.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    main_log = data_dir / "main.log"
    
    handler = logging.FileHandler(main_log)
    handler.setFormatter(logging.Formatter(config.logging.format))
    
    root_logger = logging.getLogger()
    root_logger.setLevel(config.logging.level)
    
    # Remove existing handlers to avoid duplicate logs
    for h in root_logger.handlers[:]:
        root_logger.removeHandler(h)
    
    root_logger.addHandler(handler)
    
    if config.logging.console_logging:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter(config.logging.format))
        root_logger.addHandler(console_handler)
