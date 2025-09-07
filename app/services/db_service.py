from requests import Session
from app.models.models import Attachment, Email


class DBService:
    def __init__(self, db: Session):
        self.db = db

    def add(self, obj):
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def get_attachment_by_id(self, attachment_id: str):
        return self.db.query(Attachment).filter_by(attachment_id=attachment_id).first()

    def save_attachment(self, attachment: Attachment):
        self.add(attachment)

    def get_email_by_id(self, msg_id):
        return self.db.query(Email).filter_by(gmail_message_id=msg_id).first()