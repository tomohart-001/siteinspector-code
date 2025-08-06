"""
Register earthworks routes in application factory
"""
"""
Application Factory
Handles Flask application creation and configuration
"""
from flask import Flask
import os
from typing import Optional

from config import Config
from routes import register_all_routes
from database import db_manager
from utils.logger import setup_logger
from core.error_handlers import register_error_handlers
from core.service_manager import ServiceManager
from routes.main_routes import main_route_handler
from routes.auth_routes import auth_route_handler
from routes.location_routes import location_route_handler
from routes.site_routes import site_route_handler
from routes.conversation_routes import conversation_route_handler
from routes.floorplan_routes import floorplan_route_handler
from routes.building_routes import building_route_handler
from routes.structural_routes import structural_route_handler


class AppFactory:
    """Factory for creating and configuring Flask applications"""

    @staticmethod
    def create_app() -> Flask:
        """Create and configure Flask application"""
        logger = setup_logger("AppFactory", Config.LOG_LEVEL)

        try:
            logger.info("🚀 Creating Flask application...")

            # Validate configuration
            if not Config.validate_config():
                raise ValueError("Configuration validation failed")

            # Set environment variables
            os.environ["OPENAI_API_KEY"] = Config.OPENAI_API_KEY

            # Create Flask app with explicit template and static folders
            app = Flask(__name__, 
                   template_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates'),
                   static_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static'))
            app.secret_key = Config.SECRET_KEY

            # Configure database for production
            if Config.ENVIRONMENT == 'production':
                # Set shorter timeouts for production
                os.environ['DATABASE_TIMEOUT'] = '30'
            
            # Register components
            register_error_handlers(app)
            success, errors = register_all_routes(app)

            if not success:
                logger.warning(f"Some routes failed to register: {errors}")
            else:
                logger.info("All routes registered successfully using modern registration system")

            # Database is automatically initialized by DatabaseManager
            logger.info("Database initialized successfully")

            # Initialize services
            ServiceManager.initialize_all()
            logger.info("Services initialized successfully")

            logger.info(f"✅ Application created successfully in {Config.ENVIRONMENT} mode")
            return app

        except Exception as e:
            logger.critical("Failed to create application", e)
            raise



