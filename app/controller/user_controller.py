from app.services.db_service import DBService
from app.services.user_service import UserService
from app.utils.exceptions import NotFoundError, DatabaseError


class UserController:

    @staticmethod
    async def get_user_info(user: dict, db):
        try:
            db_service = DBService(db)
            user_obj = db_service.get_user_by_id(user.get("user_id"))
            
            if not user_obj:
                raise NotFoundError("User", str(user.get("user_id")))

            return user_obj
        except NotFoundError:
            raise
        except Exception as e:
            raise DatabaseError(f"Failed to retrieve user info: {str(e)}")

    @staticmethod
    async def update_user_details(user: dict, update_details: dict, db):
        try:
            db_service = DBService(db)
            db_service.update_user_details(user.get("user_id"), update_details)
        except Exception as e:
            raise DatabaseError(f"Failed to update user details: {str(e)}")

    @staticmethod
    async def get_user_settings(user: dict, db):
        try:
            user_service = UserService(db)
            return await user_service.get_user_settings(user, db)
        except Exception as e:
            raise DatabaseError(f"Failed to retrieve user settings: {str(e)}")
