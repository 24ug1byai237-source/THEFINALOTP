from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.database.session import get_db
from app.models.user import User
from app.schemas.notification import NotificationResponse
from app.services.notification_service import NotificationService
from app.utils.serializers import notification_to_response

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", response_model=list[NotificationResponse])
def list_notifications(
    db: Session = Depends(get_db),
    current_user: Annotated[User, Depends(get_current_user)] = None,
):
    notifications = NotificationService.list_notifications(db, current_user)
    return [notification_to_response(n) for n in notifications]


@router.patch("/{notification_id}/read", status_code=204)
def mark_notification_read(
    notification_id: str,
    db: Session = Depends(get_db),
    current_user: Annotated[User, Depends(get_current_user)] = None,
):
    NotificationService.mark_read(db, notification_id, current_user)
    return None


@router.patch("/read-all", status_code=204)
def mark_all_read(
    db: Session = Depends(get_db),
    current_user: Annotated[User, Depends(get_current_user)] = None,
):
    NotificationService.mark_all_read(db, current_user)
    return None
