"""
Service Manager
Handles initialization and management of application services
"""
from utils.logger import setup_logger
from utils.error_handler import ErrorHandler, ErrorCategories, ErrorSeverity

logger = setup_logger("ServiceManager")


class ServiceManager:
    """Manages application services initialization and health"""

    _initialized = False
    _services = {}

    @classmethod
    def initialize_all(cls):
        """Initialize all application services"""
        if cls._initialized:
            return

        try:
            logger.info("Initializing application services...")

            # Import and initialize services
            from services import (
                council_service, 
                gradient_service, 
                ChatService,
                response_service,
                api_calculation_service,
                floorplan_service,
                building_service,
                beam_service
            )

            # Store service references
            cls._services = {
                'council': council_service,
                'gradient': gradient_service,
                'chat': ChatService,
                'response': response_service,
                'api_calculation': api_calculation_service,
                'floorplan': floorplan_service,
                'building': building_service,
                'beam': beam_service
            }

            # Validate critical services
            if not council_service:
                raise RuntimeError("Council service failed to initialize")

            cls._initialized = True
            logger.info("All services initialized successfully")

        except Exception as e:
            error_response = ErrorHandler.handle_error(
                e,
                category=ErrorCategories.UNKNOWN,
                severity=ErrorSeverity.CRITICAL,
                context={'operation': 'service_initialization'}
            )
            logger.critical("Service initialization failed", e, error_response['context'])
            raise

    @classmethod
    def get_service(cls, service_name: str):
        """Get a specific service by name"""
        return cls._services.get(service_name)

    @classmethod
    def health_check(cls) -> dict:
        """Check health of all services"""
        health_status = {}
        for name, service in cls._services.items():
            try:
                # Basic health check - service exists and is not None
                health_status[name] = 'healthy' if service else 'unhealthy'
            except Exception as e:
                health_status[name] = f'error: {str(e)}'

        return health_status