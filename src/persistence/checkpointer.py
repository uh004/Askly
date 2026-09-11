"""Create the LangGraph checkpointer used by the interview workflow."""

from __future__ import annotations

from typing import Any

from langgraph.checkpoint.memory import InMemorySaver


def _load_postgres_dependencies() -> tuple[type[Any], type[Any], Any]:
    """Import native PostgreSQL dependencies only when they are needed."""

    from langgraph.checkpoint.postgres import PostgresSaver
    from psycopg.rows import dict_row
    from psycopg_pool import ConnectionPool

    return ConnectionPool, PostgresSaver, dict_row


def get_checkpointer_backend(database_url: str | None) -> str:
    """Return the configured persistence backend name."""

    return "postgres" if database_url and database_url.strip() else "memory"


def create_interview_checkpointer(database_url: str | None) -> Any:
    """Use PostgreSQL when configured, otherwise keep local development simple."""

    if get_checkpointer_backend(database_url) == "memory":
        return InMemorySaver()

    (
        connection_pool_class,
        postgres_saver_class,
        dict_row,
    ) = _load_postgres_dependencies()
    pool = connection_pool_class(
        conninfo=database_url,
        min_size=0,
        max_size=5,
        kwargs={
            "autocommit": True,
            "prepare_threshold": 0,
            "row_factory": dict_row,
        },
        open=True,
    )
    return postgres_saver_class(pool)
