"""
Models package initialization.

This module ensures all models and event handlers are properly imported
and registered when the models package is loaded.
"""

# Import all models to ensure they are registered with SQLAlchemy
from .models import *

# Import Pydantic schemas
from .scheme import *
from .integration_schemas import *

# Import event handlers to ensure they are registered
from . import event_handlers

# Register event handlers (though they auto-register via decorators)
event_handlers.register_event_handlers()