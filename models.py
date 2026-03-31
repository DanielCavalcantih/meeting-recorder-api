from sqlalchemy import Column, Integer, String, DateTime
from database import Base
from datetime import datetime, timezone

class Record(Base):
    __tablename__ = "records"

    id = Column(Integer, primary_key=True, index=True)
    resume = Column(String)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

