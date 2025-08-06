
"""
Routes package initialization and route manager.
"""
import traceback
from .main_routes import MainRoutes
from .auth_routes import AuthRoutes
from .location_routes import LocationRoutes
from .site_routes import SiteRoutes
from .conversation_routes import ConversationRoutes
from .floorplan_routes import FloorplanRoutes
from .building_routes import BuildingRoutes
from .terrain_routes import TerrainRoutes
from .earthworks_routes import EarthworksRoutes
from .project_routes import ProjectRoutes
from .api_routes import ApiRoutes
from .page_routes import PageRoutes
from .team_routes import TeamRoutes
from typing import List, Tuple, Dict, Any
from flask import Flask
from utils.logger import app_logger

# Import all route handlers
from .main_routes import main_route_handler, MainRoutes
from .auth_routes import auth_route_handler, AuthRoutes
from .location_routes import location_route_handler, LocationRoutes
from .site_routes import site_route_handler, SiteRoutes
from .conversation_routes import conversation_route_handler, ConversationRoutes
from .floorplan_routes import floorplan_route_handler, FloorplanRoutes
from .building_routes import building_route_handler, BuildingRoutes
from .structural_routes import structural_route_handler, StructuralRoutes


class RouteManager:
    """
    Central route management system for the EngineRoom application.

    Handles registration of all route modules with comprehensive error handling
    and monitoring to ensure application stability.
    """

    def __init__(self):
        """Initialize the route manager with error tracking."""
        self.registered_routes: List[str] = []
        self.failed_routes: List[Tuple[str, str]] = []
        self.route_instances = {}

    def register_all_routes(self, app: Flask) -> Tuple[bool, List[str]]:
        """
        Register all application routes with the Flask app.

        This method systematically registers all route modules while maintaining
        detailed error tracking and recovery capabilities.

        Args:
            app (Flask): The Flask application instance

        Returns:
            Tuple[bool, List[str]]: Success status and list of any errors

        Raises:
            Exception: Critical errors that prevent route registration
        """
        try:
            app_logger.info("🚀 Starting comprehensive route registration process...")
            app_logger.info(f"📊 Flask app configuration: debug={app.debug}, testing={app.testing}")

            # Define route modules in order of importance
            # Critical routes first, optional features last
            route_modules = [
                ("main_routes", MainRoutes, "Core application routes"),
                ("auth_routes", AuthRoutes, "Authentication and session management"),
                ("project_routes", ProjectRoutes, "Project management"),
                ("api_routes", ApiRoutes, "General API endpoints"),
                ("page_routes", PageRoutes, "Static page rendering"),
                ("team_routes", TeamRoutes, "Team management"),
                ("location_routes", LocationRoutes, "Location selection and geocoding"),
                ("site_routes", SiteRoutes, "Site selection and inspection"),
                ("conversation_routes", ConversationRoutes, "Chat and conversation management"),
                ("floorplan_routes", FloorplanRoutes, "Floor plan processing"),
                ("building_routes", BuildingRoutes, "Building design tools"),
                ("terrain_routes", TerrainRoutes, "Terrain visualization routes"),
                ("earthworks_routes", EarthworksRoutes, "Earthworks calculation routes"),
                ("structural_routes", StructuralRoutes, "Structural analysis tools")
]

            registration_success = True

            # Register each route module with individual error handling
            for module_name, route_class, description in route_modules:
                success = self._register_route_module(app, module_name, route_class, description)
                if not success:
                    registration_success = False
                    app_logger.error(f"❌ Failed to register {module_name} - {description}")

            # Summary logging
            if registration_success:
                app_logger.info(f"✅ All routes registered successfully: {', '.join(self.registered_routes)}")
                app_logger.info(f"📈 Total registered route modules: {len(self.registered_routes)}")
            else:
                app_logger.warning(f"⚠️ Route registration completed with errors:")
                app_logger.warning(f"   ✅ Successful: {self.registered_routes}")
                app_logger.warning(f"   ❌ Failed: {[name for name, _ in self.failed_routes]}")

            # Register error handlers
            self._register_error_handlers(app)

            return registration_success, [error for _, error in self.failed_routes]

        except Exception as e:
            app_logger.critical(f"🚨 CRITICAL: Route registration system failure: {e}")
            app_logger.critical(f"Stack trace: {traceback.format_exc()}")
            raise

    def _register_route_module(self, app: Flask, module_name: str, route_class: type, description: str) -> bool:
        """
        Register a single route module with comprehensive error handling.

        Args:
            app (Flask): Flask application instance
            module_name (str): Name of the route module
            route_class (type): Route class to instantiate
            description (str): Human-readable description

        Returns:
            bool: True if registration succeeded, False otherwise
        """
        try:
            app_logger.info(f"🔧 Registering {module_name}: {description}")

            # Instantiate the route class
            route_instance = route_class()

            # Validate that the route class has required methods
            if not hasattr(route_instance, 'register_routes'):
                raise AttributeError(f"Route class {route_class.__name__} missing register_routes method")

            # Store instance for potential cleanup later
            self.route_instances[module_name] = route_instance

            # Register routes with the Flask app
            route_instance.register_routes(app)

            # Verify registration by checking Flask's URL map
            route_count = self._count_routes_for_module(app, module_name)

            self.registered_routes.append(module_name)
            app_logger.info(f"✅ {module_name} registered successfully ({route_count} routes)")

            return True

        except ImportError as e:
            error_msg = f"Import error for {module_name}: {e}"
            app_logger.error(error_msg)
            self.failed_routes.append((module_name, error_msg))
            return False

        except AttributeError as e:
            error_msg = f"Route class error for {module_name}: {e}"
            app_logger.error(error_msg)
            self.failed_routes.append((module_name, error_msg))
            return False

        except Exception as e:
            error_msg = f"Unexpected error registering {module_name}: {e}"
            app_logger.error(f"{error_msg}\nStack trace: {traceback.format_exc()}")
            self.failed_routes.append((module_name, error_msg))
            return False

    def _count_routes_for_module(self, app: Flask, module_name: str) -> int:
        """
        Count the number of routes registered for a specific module.

        Args:
            app (Flask): Flask application instance
            module_name (str): Name of the route module

        Returns:
            int: Number of routes registered
        """
        try:
            # This is an approximation - Flask doesn't directly track routes by module
            # We count the routes added since the last check
            return len([rule for rule in app.url_map.iter_rules()])
        except Exception as e:
            app_logger.warning(f"Could not count routes for {module_name}: {e}")
            return 0

    def _register_error_handlers(self, app: Flask) -> None:
        """
        Register application-wide error handlers.

        Args:
            app (Flask): Flask application instance
        """
        try:
            app_logger.info("🛡️ Registering error handlers...")

            # Check if error handlers are already registered to avoid duplicates
            existing_endpoints = [rule.endpoint for rule in app.url_map.iter_rules()]

            if 'log_frontend_error' not in existing_endpoints:
                from core.error_handlers import register_error_handlers
                register_error_handlers(app)
                app_logger.info("✅ Error handlers registered successfully")
            else:
                app_logger.info("✅ Error handlers already registered, skipping")

        except Exception as e:
            app_logger.error(f"Failed to register error handlers: {e}")
            # Don't fail the entire application for error handler issues
            pass

    def get_registration_status(self) -> dict:
        """
        Get detailed status of route registration.

        Returns:
            dict: Comprehensive status information
        """
        return {
            'total_modules': len(self.registered_routes) + len(self.failed_routes),
            'successful_modules': len(self.registered_routes),
            'failed_modules': len(self.failed_routes),
            'registered_routes': self.registered_routes.copy(),
            'failed_routes': self.failed_routes.copy(),
            'success_rate': len(self.registered_routes) / (len(self.registered_routes) + len(self.failed_routes)) * 100 if (self.registered_routes or self.failed_routes) else 0
        }


def register_all_routes(app: Flask) -> Tuple[bool, List[str]]:
    """
    Main entry point for route registration.

    This function provides a clean interface for the app factory to register
    all routes while maintaining backward compatibility.

    Args:
        app (Flask): Flask application instance

    Returns:
        Tuple[bool, List[str]]: Success status and list of any errors
    """
    try:
        app_logger.info("🎯 Initializing route registration system...")

        route_manager = RouteManager()
        success, errors = route_manager.register_all_routes(app)

        # Log final status
        status = route_manager.get_registration_status()
        app_logger.info(f"📊 Route Registration Summary:")
        app_logger.info(f"   Success Rate: {status['success_rate']:.1f}%")
        app_logger.info(f"   Successful: {status['successful_modules']}/{status['total_modules']}")

        if errors:
            app_logger.warning(f"   Errors encountered: {len(errors)}")
            for error in errors:
                app_logger.warning(f"     - {error}")

        return success, errors

    except Exception as e:
        app_logger.critical(f"🚨 Route registration system completely failed: {e}")
        return False, [str(e)]


# Legacy support - export route handlers for backward compatibility
__all__ = [
    'register_all_routes',
    'RouteManager',
    'main_route_handler',
    'auth_route_handler',
    'location_route_handler',
    'site_route_handler',
    'conversation_route_handler',
    'floorplan_route_handler',
    'building_route_handler',
    'structural_route_handler'
]
