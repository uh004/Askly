from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

from langgraph.checkpoint.memory import InMemorySaver

from src.persistence.checkpointer import (
    create_interview_checkpointer,
    get_checkpointer_backend,
)


class CheckpointerFactoryTest(unittest.TestCase):
    def test_uses_memory_without_database_url(self) -> None:
        checkpointer = create_interview_checkpointer(None)

        self.assertIsInstance(checkpointer, InMemorySaver)
        self.assertEqual(get_checkpointer_backend(""), "memory")

    @patch("src.persistence.checkpointer._load_postgres_dependencies")
    def test_uses_postgres_with_database_url(self, dependency_loader: Mock) -> None:
        pool_class = Mock()
        postgres_saver_class = Mock()
        dict_row = Mock()
        dependency_loader.return_value = (
            pool_class,
            postgres_saver_class,
            dict_row,
        )
        pool = pool_class.return_value
        expected_checkpointer = postgres_saver_class.return_value

        checkpointer = create_interview_checkpointer(
            "postgresql://askly:secret@db.example.com/askly"
        )

        self.assertIs(checkpointer, expected_checkpointer)
        self.assertEqual(
            get_checkpointer_backend("postgresql://db.example.com/askly"),
            "postgres",
        )
        pool_class.assert_called_once_with(
            conninfo="postgresql://askly:secret@db.example.com/askly",
            min_size=0,
            max_size=5,
            kwargs={
                "autocommit": True,
                "prepare_threshold": 0,
                "row_factory": dict_row,
            },
            open=True,
        )
        postgres_saver_class.assert_called_once_with(pool)


if __name__ == "__main__":
    unittest.main()
