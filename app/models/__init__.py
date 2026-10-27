"""SQLAlchemy models. Importing this package registers every model."""
from app.models.week import Week
from app.models.slot import Slot
from app.models.recurring import RecurringTemplate
from app.models.log import Log

__all__ = ["Week", "Slot", "RecurringTemplate", "Log"]
