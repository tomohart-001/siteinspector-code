"""
Application Constants
Centralized configuration values for EngineRoom
"""

# =============================================================================
# UI Configuration
# =============================================================================
MAX_MESSAGE_LENGTH = 1000
MAX_CONVERSATION_HISTORY = 50
STREAMING_WORD_DELAY = 0.01  # Seconds between streamed words

# =============================================================================
# Database Configuration  
# =============================================================================
DEFAULT_SESSION_TIMEOUT_HOURS = 24
MAX_FEEDBACK_PER_SESSION = 100
DB_CONNECTION_TIMEOUT = 30  # Seconds
DB_QUERY_TIMEOUT = 60  # Seconds

# =============================================================================
# AI Agent Configuration
# =============================================================================
DEFAULT_MODEL = "gpt-4.1-nano"
MAX_SEARCH_RESULTS = 5
MAX_AGENT_ITERATIONS = 10
AGENT_TIMEOUT_SECONDS = 120

# =============================================================================
# External Service Configuration
# =============================================================================
# Vector Store IDs for different knowledge bases
STANDARDS_VECTOR_STORE_ID = "vs_6850d2ea29c88191a36bda16b22a3f26"
ZONING_VECTOR_STORE_ID = "vs_684a312456bc8191bafa246be88e96ff"

# =============================================================================
# Error Messages
# =============================================================================
class ErrorMessages:
    NO_MESSAGE = "No message provided"
    AUTH_REQUIRED = "Authentication required"
    DATABASE_CONNECTION = "Database connection failed"
    INVALID_SESSION = "Invalid session identifier"
    MESSAGE_TOO_LONG = f"Message exceeds {MAX_MESSAGE_LENGTH} characters"
    CALCULATION_NOT_SUPPORTED = "I have not been programmed for that calculation yet."
    RATE_LIMIT_EXCEEDED = "Too many requests. Please wait before sending another message."
    AGENT_TIMEOUT = "Request timed out. Please try again."

# =============================================================================
# Success Messages
# =============================================================================
# =============================================================================
# Application Metadata
# =============================================================================
APP_NAME = "EngineRoom"
APP_VERSION = "1.0.0"
APP_DESCRIPTION = "Engineering AI, Aligned with NZ Standards"

# =============================================================================
# Supported Standards Information
# =============================================================================
SUPPORTED_STANDARDS = [
    {
        "code": "NZS 3404:1997",
        "name": "Steel Structures Standard",
        "category": "Structural"
    },
    {
        "code": "NZS 1170.5:2004", 
        "name": "Structural Design Actions (Earthquake)",
        "category": "Seismic"
    },
    {
        "code": "NZS 3604:2011",
        "name": "Timber-Framed Buildings", 
        "category": "Timber"
    },
    {
        "code": "NZS 3101:2006",
        "name": "Concrete Structures (A1–A3)",
        "category": "Concrete"
    },
    {
        "code": "Building Code Handbook 3E Amdt13",
        "name": "New Zealand Building Code",
        "category": "Building Code"
    },
    {
        "code": "NZS 3605:2001",
        "name": "Timber Piles & Poles",
        "category": "Timber"
    },
    {
        "code": "NZS 4219:2009",
        "name": "Seismic Performance of Engineering Systems",
        "category": "Seismic"
    },
    {
        "code": "NZS 4121:2001",
        "name": "Design for Access & Mobility",
        "category": "Accessibility"
    },
    {
        "code": "SNZ-TS 3404:2018",
        "name": "Durability for Steel Structures",
        "category": "Durability"
    }
]