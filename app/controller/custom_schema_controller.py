"""Custom Schema Controller Module"""

from sqlalchemy.orm import Session

from app.models.scheme import CustomSchemaCreate, CustomSchemaUpdate, FullSchemaResponse
from app.services.custom_schema_service import CustomSchemaService
from app.utils.exceptions import NotFoundError, DatabaseError


class CustomSchemaController:
    """Controller for custom schema endpoints"""

    @staticmethod
    async def get_schema(user: dict, db: Session):
        """Get the full schema (default + custom fields) for the authenticated user"""
        try:
            user_id = user.get("user_id")
            service = CustomSchemaService(db)
            return service.get_full_schema(user_id)
        except Exception as e:
            raise DatabaseError(f"Failed to retrieve schema: {str(e)}")

    @staticmethod
    async def save_custom_schema(payload: CustomSchemaCreate, user: dict, db: Session):
        """Create or update custom schema for the authenticated user"""
        try:
            user_id = user.get("user_id")
            service = CustomSchemaService(db)
            schema = service.create_or_update_schema(user_id, payload)
            return {
                "message": "Custom schema saved successfully",
                "data": service.to_response(schema)
            }
        except DatabaseError:
            raise
        except Exception as e:
            raise DatabaseError(f"Failed to save custom schema: {str(e)}")

    @staticmethod
    async def update_custom_schema(payload: CustomSchemaUpdate, user: dict, db: Session):
        """Update existing custom schema for the authenticated user"""
        try:
            user_id = user.get("user_id")
            service = CustomSchemaService(db)
            schema = service.update_schema(user_id, payload)
            return {
                "message": "Custom schema updated successfully",
                "data": service.to_response(schema)
            }
        except NotFoundError:
            raise
        except DatabaseError:
            raise
        except Exception as e:
            raise DatabaseError(f"Failed to update custom schema: {str(e)}")

    @staticmethod
    async def delete_custom_schema(user: dict, db: Session):
        """Delete custom schema for the authenticated user"""
        try:
            user_id = user.get("user_id")
            service = CustomSchemaService(db)
            deleted = service.delete_schema(user_id)
            
            if not deleted:
                raise NotFoundError("Custom Schema", str(user_id))
            
            return {"message": "Custom schema deleted successfully"}
        except NotFoundError:
            raise
        except Exception as e:
            raise DatabaseError(f"Failed to delete custom schema: {str(e)}")
