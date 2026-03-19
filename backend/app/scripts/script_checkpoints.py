from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

from sqlalchemy import text

from app.core.database import SessionLocal

CHECKPOINT_TABLE_SQL = """
create table if not exists script_checkpoints (
    script_name varchar(120) not null,
    step_name varchar(120) not null,
    status varchar(30) not null,
    detail text null,
    started_at timestamptz null,
    completed_at timestamptz null,
    updated_at timestamptz null,
    primary key (script_name, step_name)
)
"""

ALTER_TABLE_STATEMENTS = (
    "alter table script_checkpoints add column if not exists started_at timestamptz null",
    "alter table script_checkpoints add column if not exists updated_at timestamptz null",
)


def ensure_checkpoint_table(session) -> None:
    session.execute(text(CHECKPOINT_TABLE_SQL))
    for statement in ALTER_TABLE_STATEMENTS:
        session.execute(text(statement))
    session.commit()


def is_completed(session, script_name: str, step_name: str) -> bool:
    result = session.execute(
        text(
            """
            select 1
            from script_checkpoints
            where script_name = :script_name
              and step_name = :step_name
              and status = 'completed'
            """
        ),
        {"script_name": script_name, "step_name": step_name},
    ).first()
    return result is not None


def mark_status(
    session,
    script_name: str,
    step_name: str,
    status: str,
    detail: str | None = None,
    *,
    started_at: datetime | None = None,
    completed_at: datetime | None = None,
) -> None:
    session.execute(
        text(
            """
            insert into script_checkpoints (
                script_name,
                step_name,
                status,
                detail,
                started_at,
                completed_at,
                updated_at
            )
            values (
                :script_name,
                :step_name,
                :status,
                :detail,
                :started_at,
                :completed_at,
                :updated_at
            )
            on conflict (script_name, step_name) do update
            set status = excluded.status,
                detail = excluded.detail,
                started_at = coalesce(script_checkpoints.started_at, excluded.started_at),
                completed_at = excluded.completed_at,
                updated_at = excluded.updated_at
            """
        ),
        {
            "script_name": script_name,
            "step_name": step_name,
            "status": status,
            "detail": detail,
            "started_at": started_at,
            "completed_at": completed_at,
            "updated_at": datetime.now(UTC),
        },
    )
    session.commit()


def mark_started(session, script_name: str, step_name: str) -> None:
    now = datetime.now(UTC)
    mark_status(
        session,
        script_name,
        step_name,
        "in_progress",
        "Step started",
        started_at=now,
        completed_at=None,
    )


def mark_failed(session, script_name: str, step_name: str, detail: str | None = None) -> None:
    mark_status(session, script_name, step_name, "failed", detail, completed_at=None)


def mark_completed(session, script_name: str, step_name: str, detail: str | None = None) -> None:
    mark_status(
        session,
        script_name,
        step_name,
        "completed",
        detail,
        completed_at=datetime.now(UTC),
    )


def run_checkpoint_step(
    script_name: str,
    step_name: str,
    callback: Callable[[], str | None],
) -> None:
    checkpoint_session = SessionLocal()
    try:
        ensure_checkpoint_table(checkpoint_session)
        if is_completed(checkpoint_session, script_name, step_name):
            print(f"[skip] {script_name}:{step_name} already completed")
            return
        mark_started(checkpoint_session, script_name, step_name)
    finally:
        checkpoint_session.close()

    try:
        detail = callback()
    except Exception as exc:
        checkpoint_session = SessionLocal()
        try:
            ensure_checkpoint_table(checkpoint_session)
            mark_failed(checkpoint_session, script_name, step_name, str(exc))
        finally:
            checkpoint_session.close()
        raise

    checkpoint_session = SessionLocal()
    try:
        ensure_checkpoint_table(checkpoint_session)
        mark_completed(checkpoint_session, script_name, step_name, detail)
    finally:
        checkpoint_session.close()

    print(f"[done] {script_name}:{step_name}")
