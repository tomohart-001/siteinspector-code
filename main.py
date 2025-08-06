"""
EngineRoom - Engineering AI Application
Main application entry point with improved modular architecture
"""
import os
from core.app_factory import AppFactory
from utils.logger import setup_logger, app_logger
from config import Config


def create_app():
    """Create Flask application using factory pattern"""
    return AppFactory.create_app()


def main():
    """Main entry point"""
    logger = setup_logger("Main", Config.LOG_LEVEL)

    try:
        logger.info("🚀 Starting EngineRoom application...")

        # Create application
        app = create_app()

        # Start server with timeout configuration
        port = int(os.getenv('PORT', 5000))
        logger.info(f"Starting server on 0.0.0.0:{port} in {Config.ENVIRONMENT} mode")
        
        if Config.ENVIRONMENT == 'production':
            # Production configuration
            app.run(
                host='0.0.0.0',
                port=port,
                debug=False,
                threaded=True,
                use_reloader=False
            )
        else:
            # Development configuration
            app.run(
                host='0.0.0.0',
                port=port,
                debug=Config.DEBUG,
                threaded=True
            )

    except Exception as e:
        app_logger.critical("Application startup failed", e)
        raise


if __name__ == '__main__':
    main()