"""
Database event handlers for model lifecycle events.

This module contains SQLAlchemy event listeners that handle automatic
operations when certain database events occur.
"""

from sqlalchemy.event import listens_for
from sqlalchemy.orm import Session

from . import Email, Source, SourceType


@listens_for(Email, 'after_insert')
def create_email_source(mapper, connection, target):
    """
    Create a Source entry automatically after an Email is saved.
    
    This event handler ensures that every email gets a corresponding
    source record for unified tracking across the system.
    
    Args:
        mapper: SQLAlchemy mapper
        connection: Database connection
        target: The Email instance that was inserted
    """
    try:
        # Create a new Source record for this email
        source_insert = Source.__table__.insert().values(
            type=SourceType.email,
            external_id=str(target.id)
        )
        result = connection.execute(source_insert)
        source_id = result.inserted_primary_key[0]
        
        # Update the email with the newly created source_id
        email_update = Email.__table__.update().where(
            Email.__table__.c.id == target.id
        ).values(source_id=source_id)
        connection.execute(email_update)
        
    except Exception as e:
        # Log the error but don't raise to avoid breaking the email insertion
        print(f"Error creating source for email {target.id}: {e}")
        # In production, you might want to use proper logging instead of print


def register_event_handlers():
    """
    Register all event handlers.
    
    This function can be called during application startup to ensure
    all event handlers are properly registered. Currently, the handlers
    are registered automatically via the @listens_for decorators, but
    this function provides a centralized place for any additional setup.
    """
    # Event handlers are automatically registered via @listens_for decorators
    # This function is provided for any future manual registration needs
    pass