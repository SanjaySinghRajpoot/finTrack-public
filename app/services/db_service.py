from typing import List

from requests import Session
from app.models.models import Attachment, Email, ProcessedEmailData


class DBService:
    def __init__(self, db: Session):
        self.db = db

    def add(self, obj):
        try:
            self.db.add(obj)
            self.db.commit()
            self.db.refresh(obj)
            return obj
        except Exception as e:
            raise e


    def get_attachment_by_id(self, attachment_id: str):
        return self.db.query(Attachment).filter_by(attachment_id=attachment_id).first()

    def save_attachment(self, attachment: Attachment):
        self.add(attachment)

    def save_proccessed_email_data(self, processed_email_data: ProcessedEmailData):
        self.add(processed_email_data)

    def get_processed_data(self, user_id: int) -> List[ProcessedEmailData]:
        return (
            self.db.query(ProcessedEmailData)
            .filter(ProcessedEmailData.user_id == user_id)
            .all()
        )

    def get_email_by_id(self, msg_id):
        return self.db.query(Email).filter_by(gmail_message_id=msg_id).first()