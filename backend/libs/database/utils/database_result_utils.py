from typing import Any, cast

from sqlalchemy import CursorResult, Result


class DatabaseResultUtils:
    """Reads what SQLAlchemy's typing hides on the result of a statement."""

    @staticmethod
    def get_row_count(write_result: Result[Any]) -> int:
        """The number of rows an UPDATE or DELETE matched."""
        # execute() is typed to return Result, but a write's result is a CursorResult
        return cast(CursorResult[Any], write_result).rowcount
