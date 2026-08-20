from contextlib import AbstractContextManager

from sqlalchemy import Engine, func, create_engine, DateTime, String, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker
from datetime import datetime
from enum import StrEnum
from functools import cache
from tabletop_tactician.config import get_settings


class Status(StrEnum):
    UNKNOWN = "UNKNOWN"
    PENDING = "PENDING"
    ERROR = "ERROR"
    DONE = "DONE"


class Base(DeclarativeBase):
    pass


class UserTable(Base):
    __tablename__ = "users"

    user_id: Mapped[str] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=True)
    enabled: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    num_reports_run: Mapped[int] = mapped_column(default=0)


class ReportsTable(Base):
    __tablename__ = "reports"

    job_id: Mapped[str] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"))
    attacking_army: Mapped[str] = mapped_column(nullable=False)
    defending_army: Mapped[str] = mapped_column(nullable=False)
    result: Mapped[str | None]
    status: Mapped[str] = mapped_column(nullable=False, default=Status.UNKNOWN)
    error_msg: Mapped[str | None]

@cache     
def get_session_maker() -> sessionmaker[Session]:   
    return sessionmaker(get_engine(), expire_on_commit=False)

@cache
def get_engine() -> Engine:
    settings = get_settings()
    return create_engine(url=settings.database_url.get_secret_value(), pool_pre_ping=True)


if __name__ == "__main__":

    with Session(get_engine()) as session:
        stmt = select(func.now())
        print(session.scalar(statement=stmt))
