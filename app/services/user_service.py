from app.services.db_service import DBService
from lib.requests import Session


class UserService:

    async def get_user_settings(self, user: dict, db: Session):
        try:
            db_service = DBService(db)
            integrations = db_service.get_user_integrations(user.get("user_id"))

            results = []
            for i in integrations:
                data = {
                    "integration_id": str(i.id),
                    "integration_type": i.integration_type.value,
                    "status": i.status.value,
                    "error_message": i.error_message,
                    "last_synced_at": i.last_synced_at,
                    "next_sync_at": i.next_sync_at,
                    "sync_interval_minutes": i.sync_interval_minutes,
                    "last_sync_duration": i.last_sync_duration,
                    "total_syncs": i.total_syncs,
                    "created_at": i.created_at,
                    "updated_at": i.updated_at,
                }

                # 👇 Add integration-specific details
                if i.integration_type.name.lower() == "email" and i.email_config:
                    data.update({
                        "connected_email": i.email_config.email_address,
                        "provider": i.email_config.provider,
                        "verified": i.email_config.verified,
                        "connected_at": i.email_config.connected_at,
                        "expires_at": i.email_config.expires_at,
                    })

                elif i.integration_type.name.lower() == "whatsapp" and i.whatsapp_config:
                    data.update({
                        "connected_number": i.whatsapp_config.phone_number,
                        "verified": i.whatsapp_config.verified,
                        "connected_at": i.whatsapp_config.connected_at,
                    })

                results.append(data)

            return results
        except Exception as e:
            raise e