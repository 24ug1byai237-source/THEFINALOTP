import uuid

from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError
from app.models.enums import NotificationType, UserRole
from app.models.farm import Farm
from app.models.notification import Notification
from app.models.user import User, UserFarmAssignment
from app.utils.helpers import generate_id


class NotificationService:
    @staticmethod
    def create(
        db: Session,
        title: str,
        message: str,
        notification_type: NotificationType,
        target_role: UserRole | None = None,
        broadcast_all: bool = False,
        action_url: str | None = None,
        recipient_user_id: uuid.UUID | str | None = None,
    ) -> Notification:
        """
        Create a notification.

        • recipient_user_id → delivered to exactly that user (used for
          farm-specific events: this farm's incident was verified, this
          farmer's evidence was rejected, etc). Preferred whenever the event
          concerns a specific person/farm.
        • target_role (no recipient_user_id) → a role-wide "team inbox" item,
          appropriate for things like "evidence awaiting review" where any
          vet with access should see it. NOT appropriate for farmer-facing,
          farm-specific events — those must use recipient_user_id instead, or
          NotificationService.notify_farm_farmers below.
        • broadcast_all → platform-wide alert visible to everyone.
        """
        notification = Notification(
            id=generate_id("NOTIF"),
            user_id=uuid.UUID(str(recipient_user_id)) if recipient_user_id else None,
            title=title,
            message=message,
            notification_type=notification_type,
            target_role=target_role,
            broadcast_all=broadcast_all,
            action_url=action_url,
        )
        db.add(notification)
        db.flush()
        return notification

    @staticmethod
    def notify_farm_farmers(
        db: Session,
        farm: Farm,
        title: str,
        message: str,
        notification_type: NotificationType,
        action_url: str | None = None,
    ) -> list[Notification]:
        """
        Deliver a farm-specific notification to exactly the farmer(s)
        assigned to `farm` — never to every farmer on the platform. This is
        the fix for notifications like "Incident Verified" or "Evidence
        Rejected" that used to broadcast to target_role=FARMER regardless of
        which farm the event actually happened on.
        """
        farmer_user_ids = {
            assignment.user_id
            for assignment in farm.user_assignments
            if assignment.user.role == UserRole.FARMER
        }
        return [
            NotificationService.create(
                db,
                title=title,
                message=message,
                notification_type=notification_type,
                action_url=action_url,
                recipient_user_id=user_id,
            )
            for user_id in farmer_user_ids
        ]

    @staticmethod
    def _visible_filter(query, user: User):
        """Scope a Notification query to what `user` is allowed to see."""
        return query.filter(
            (Notification.user_id == user.id)
            | (Notification.broadcast_all.is_(True))
            | (
                (Notification.user_id.is_(None))
                & (Notification.target_role == user.role)
            )
        )

    @staticmethod
    def list_notifications(db: Session, user: User | None = None) -> list[Notification]:
        if user is None:
            return []
        query = db.query(Notification).order_by(Notification.created_at.desc())
        query = NotificationService._visible_filter(query, user)
        return query.limit(100).all()

    @staticmethod
    def mark_read(db: Session, notification_id: str, user: User) -> None:
        notification = db.query(Notification).filter(Notification.id == notification_id).first()
        if not notification:
            return
        visible = NotificationService._visible_filter(
            db.query(Notification).filter(Notification.id == notification_id), user
        ).first()
        if not visible:
            # Don't leak existence of notifications the user can't see, and
            # don't let a user mark someone else's targeted notification read.
            raise ForbiddenError("You do not have access to this notification.")
        notification.read = True
        db.commit()

    @staticmethod
    def mark_all_read(db: Session, user: User) -> None:
        # Only marks notifications visible to this user — never every
        # notification in the system for every user.
        query = NotificationService._visible_filter(
            db.query(Notification).filter(Notification.read.is_(False)), user
        )
        ids = [n.id for n in query.all()]
        if ids:
            db.query(Notification).filter(Notification.id.in_(ids)).update(
                {"read": True}, synchronize_session=False
            )
        db.commit()
