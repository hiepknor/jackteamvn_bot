import asyncio

import pytest

from database.connection import DatabaseConnection


def test_database_connection_close_resets_connection(tmp_path):
    connection = DatabaseConnection(str(tmp_path / "test.db"))

    async def scenario():
        await connection.connect()
        first = connection.connection

        await connection.connect()
        assert connection.connection is first

        await connection.close()
        with pytest.raises(RuntimeError):
            _ = connection.connection

        await connection.connect()
        assert connection.connection is not first
        await connection.close()

    asyncio.run(scenario())
