"""
Tests for the dependency injection container.
"""

import pytest
from unittest.mock import Mock, MagicMock
from typing import Dict, Any, Type, Optional

# Import the DI container
from job_application_automation.src.di import DIContainer, inject, injectable, inject_param

# Test interfaces and implementations
class IService:
    def do_something(self) -> str:
        """Perform some action and return a string result."""
        raise NotImplementedError
        
    @classmethod
    def create(cls) -> 'IService':
        """Factory method to create an instance."""
        return cls()

class ConcreteService(IService):
    def do_something(self) -> str:
        return "ConcreteService"

class SecondService(IService):
    def do_something(self) -> str:
        return "SecondService"

class ServiceA(IService):
    def do_something(self) -> str:
        return "ServiceA"

class ServiceB(IService):
    def __init__(self, name: str = "ServiceB"):
        self.name = name
    
    def do_something(self) -> str:
        return self.name

class DependentService:
    def __init__(self, service: IService):
        self.service = service
    
    def execute(self) -> str:
        return f"Dependent: {self.service.do_something()}"

# Fixtures
@pytest.fixture
def container():
    """Create a fresh container for each test."""
    return DIContainer()

def test_register_and_resolve(container):
    """Test registering and resolving a simple service."""
    # Register the service
    container.bind(IService, ServiceA)
    
    # Resolve the service
    service = container.resolve(IService)
    
    # Verify the service is of the correct type
    assert isinstance(service, ServiceA)
    assert service.do_something() == "ServiceA"

def test_singleton_behavior(container):
    """Test that the same instance is returned for singleton services."""
    # Register as singleton (default)
    container.bind(IService, ServiceA)
    
    # Resolve twice
    instance1 = container.resolve(IService)
    instance2 = container.resolve(IService)
    
    # Should be the same instance
    assert instance1 is instance2

def test_transient_behavior(container):
    """Test that a new instance is created each time for non-singleton services."""
    # Register as transient
    container.bind(IService, ServiceA, singleton=False)
    
    # Resolve twice
    instance1 = container.resolve(IService)
    instance2 = container.resolve(IService)
    
    # Should be different instances
    assert instance1 is not instance2
    assert isinstance(instance1, ServiceA)
    assert isinstance(instance2, ServiceA)

def test_resolve_with_parameters(container):
    """Test resolving a service with constructor parameters."""
    # Register with a factory function that provides parameters
    container.bind(IService, lambda: ServiceB("CustomName"))
    
    # Resolve the service
    service = container.resolve(IService)
    
    # Should use the custom name
    assert service.do_something() == "CustomName"

def test_dependency_injection(container):
    """Test that dependencies are automatically injected."""
    # Register dependencies
    container.bind(IService, ServiceA)
    container.bind(DependentService, lambda: DependentService(container.resolve(IService)))
    
    # Resolve a service with dependencies
    dependent = container.resolve(DependentService)
    
    # The dependency should be injected
    assert isinstance(dependent.service, ServiceA)
    assert dependent.execute() == "Dependent: ServiceA"

def test_resolve_unregistered_interface(container):
    """Test resolving an unregistered interface raises an error."""
    class UnregisteredInterface(IService):
        def do_something(self):
            return "Unregistered"
    
    # Clear any existing instances to ensure clean state
    if hasattr(container, '_instances'):
        container._instances.clear()
    if hasattr(container, '_bindings'):
        container._bindings.clear()
            
    # This should raise a ValueError since we haven't registered UnregisteredInterface
    with pytest.raises(ValueError, match="No binding found for"):
        container.resolve(UnregisteredInterface)
    
    # Now register it and try again
    container.bind(UnregisteredInterface, lambda: UnregisteredInterface())
    instance = container.resolve(UnregisteredInterface)
    assert instance.do_something() == "Unregistered"

def test_register_instance(container):
    """Test registering an existing instance."""
    # Create an instance
    instance = ServiceB("Custom")
    
    # Register the instance
    container.instance(IService, instance)
    
    # Resolve should return the same instance
    assert container.resolve(IService) is instance
    assert container.resolve(IService).do_something() == "Custom"

def test_injectable_decorator():
    """Test the @injectable decorator."""
    # Reset the global container for this test
    from job_application_automation.src.di import container as global_container
    
    try:
        # Apply the decorator
        @injectable()
        class DecoratedService(IService):
            def do_something(self) -> str:
                return "Decorated"
        
        # Should be able to resolve the decorated service
        service = global_container.resolve(DecoratedService)
        assert isinstance(service, DecoratedService)
        assert service.do_something() == "Decorated"
        
    finally:
        # Clean up
        if hasattr(global_container, '_bindings') and IService in global_container._bindings:
            del global_container._bindings[IService]

def test_inject_decorator(container):
    """Test the @inject decorator with different injection patterns."""
    # Register services
    container.bind(IService, ConcreteService, singleton=True)
    
    # Clear any existing instances to ensure clean state
    if hasattr(container, '_instances'):
        container._instances.clear()
    
    # Test 1: Basic injection with @inject and inject_param
    @inject
    def process(service: IService = inject_param(IService)) -> str:
        return service.do_something()
    
    result = process()
    assert result == "ConcreteService"
    
    # Test 2: Explicit parameter should override injection
    explicit = SecondService()
    result = process(explicit)
    assert result == "SecondService"
    
    # Test 3: Multiple parameters with injection
    @inject
    def process_multi(
        svc1: IService = inject_param(IService), 
        svc2: IService = None
    ) -> tuple:
        return (
            svc1.do_something() if svc1 else "NoSvc1",
            svc2.do_something() if svc2 else "NoSvc2"
        )
    
    # Test with only first parameter injected
    result1, result2 = process_multi()
    assert result1 == "ConcreteService"
    assert result2 == "NoSvc2"
    
    # Test with second parameter provided
    result1, result2 = process_multi(svc2=SecondService())
    assert result1 == "ConcreteService"
    assert result2 == "SecondService"
    
    # Test 4: Class-based injection
    @inject
    class InjectedClass:
        def __init__(self, service: IService = inject_param(IService)):
            self.service = service
        
        def call_service(self) -> str:
            return self.service.do_something()
    
    instance = InjectedClass()
    assert instance.call_service() == "ConcreteService"
    
    # Test with explicit service
    instance = InjectedClass(SecondService())
    assert instance.call_service() == "SecondService"

def test_configure_container(monkeypatch, tmp_path):
    """Test that configure_container sets up all required services."""
    # Mock the imports to avoid loading actual implementations
    mock_browser = MagicMock()
    mock_scraper = MagicMock()
    mock_linkedin = MagicMock()
    mock_resume_gen = MagicMock()
    mock_tracker = MagicMock()
    mock_ats = MagicMock()
    
    # Create test directories
    data_dir = tmp_path / "data"
    log_dir = tmp_path / "logs"
    data_dir.mkdir()
    log_dir.mkdir()
    
    # Setup monkeypatch for imports
    monkeypatch.setattr('job_application_automation.src.utils.browser_automation.JobSearchBrowser', mock_browser)
    monkeypatch.setattr('job_application_automation.src.utils.web_scraping.JobDetailsScraper', mock_scraper)
    monkeypatch.setattr('job_application_automation.src.job_sources.linkedin_integration.LinkedInIntegration', mock_linkedin)
    monkeypatch.setattr('job_application_automation.src.resume_cover_letter_generator.ResumeGenerator', mock_resume_gen)
    monkeypatch.setattr('job_application_automation.src.application_tracker.ApplicationTracker', mock_tracker)
    monkeypatch.setattr('job_application_automation.src.ats_integration.ATSIntegrationManager', mock_ats)
    
    # Mock the ATS manager's load_state method
    mock_ats.return_value.load_state.return_value = None
    
    # Create a mock config
    class MockConfig:
        def __init__(self):
            self.data_dir = str(data_dir)
            self.logging = type('Logging', (), {
                'log_dir': str(log_dir),
                'format': '%(message)s',
                'level': 'INFO',
                'console_logging': True
            })
            self.browser = {}
            self.crawl = {}
            self.linkedin = {}
            self.llm = {}
    
    # Import and call configure_container
    from job_application_automation.src.di import configure_container, container
    configure_container(MockConfig())
    
    # Verify the container is properly configured
    from job_application_automation.src.utils.browser_automation import JobSearchBrowser
    from job_application_automation.src.utils.web_scraping import JobDetailsScraper
    from job_application_automation.src.job_sources.linkedin_integration import LinkedInIntegration
    from job_application_automation.src.resume_cover_letter_generator import ResumeGenerator
    from job_application_automation.src.application_tracker import ApplicationTracker
    from job_application_automation.src.ats_integration import ATSIntegrationManager
    
    # Test resolving each service
    browser = container.resolve(JobSearchBrowser)
    assert browser is not None
    
    scraper = container.resolve(JobDetailsScraper)
    assert scraper is not None
    
    linkedin = container.resolve(LinkedInIntegration)
    assert linkedin is not None
    
    resume_gen = container.resolve(ResumeGenerator)
    assert resume_gen is not None
    
    tracker = container.resolve(ApplicationTracker)
    assert tracker is not None
    
    ats = container.resolve(ATSIntegrationManager)
    assert ats is not None
    assert ats.load_state.called
