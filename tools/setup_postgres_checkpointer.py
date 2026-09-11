"""Create the LangGraph checkpoint tables in the configured PostgreSQL DB."""

from __future__ import annotations

from src.config import DATABASE_URL


def main() -> None:
    if not DATABASE_URL:
        raise SystemExit(
            "DATABASE_URL이 없습니다. .env 또는 배포 환경변수를 먼저 설정하세요."
        )

    from langgraph.checkpoint.postgres import PostgresSaver

    with PostgresSaver.from_conn_string(DATABASE_URL) as checkpointer:
        checkpointer.setup()

    print("LangGraph PostgreSQL 체크포인터 테이블 준비가 완료되었습니다.")


if __name__ == "__main__":
    main()
