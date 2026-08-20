from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import update
import structlog
from tabletop_tactician.persistence.db import get_session_maker, UserTable, ReportsTable
from tabletop_tactician.models.reports import ReportModel, UserModel


logger = structlog.get_logger()


def get_or_create_user(user_id: str) -> UserModel:
    with get_session_maker().begin() as session:
        try:
            # this is idempotent, if we just did an add or an isert without .on_conflict_do_nothing
            # and ran the same batch again it would throw an IntegrityError , this just ignores duplicates
            # if in the future i decide i want to update i can just change to .on_conflict_do_update(...)
            session.execute(
                insert(UserTable).values(user_id=user_id).on_conflict_do_nothing(index_elements=[UserTable.user_id])
            )

            user = session.get(UserTable, user_id)
            if user is None:
                raise RuntimeError(f"user {user_id} neither inserted nor found")

            return UserModel.model_validate(user)  # return a Pydantic model of the user
        except Exception:
            logger.exception("Error ensuring user exists", user_id=user_id)
            raise


def create_pending_report(job_id: str, user_id: str, attacking_army: str, defending_army: str) -> None:
    with get_session_maker().begin() as session:
        try:
            report = ReportsTable(
                job_id=job_id,
                user_id=user_id,
                attacking_army=attacking_army,
                defending_army=defending_army,
                status="PENDING",
            )
            session.add(report)
        except Exception:
            logger.exception("Error creating pending report", job_id=job_id, user_id=user_id)
            raise


def get_report(job_id: str) -> ReportModel | None:
    with get_session_maker().begin() as session:
        try:
            report = session.get(ReportsTable, job_id)
            return ReportModel.model_validate(report) if report else None
        except Exception:
            logger.exception("Error getting report", job_id=job_id)
            raise


def mark_report_failed(job_id: str, error_msg: str) -> None:
    with get_session_maker().begin() as session:
        try:
            report = session.get(ReportsTable, job_id)
            if report is None:
                raise ValueError(f"Report with job_id {job_id} not found")
            report.status = "ERROR"
            report.error_msg = error_msg
            session.add(report)
        except Exception:
            logger.exception("Error marking report failed", job_id=job_id)
            raise


def mark_report_done(job_id: str, user_id: str, result: str) -> None:
    with get_session_maker().begin() as session:
        try:
            report = session.get(ReportsTable, job_id)
            if report is None:
                raise ValueError(f"Report with job_id {job_id} not found")

            report.status = "DONE"
            report.result = result
            session.add(report)

            stmt = (
                update(UserTable)
                .where(UserTable.user_id == user_id)
                .values(num_reports_run=UserTable.num_reports_run + 1)
            )
            session.execute(stmt)
        except Exception:
            logger.exception("Error marking report done", job_id=job_id)
            raise
