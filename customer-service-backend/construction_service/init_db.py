"""Create missing AI state tables. Existing tables/data are never altered."""
import argparse
import asyncio

from sqlalchemy.engine import make_url


async def initialize(expected_database: str) -> None:
    from construction_service.config.settings import settings
    from construction_service.model.base import Base
    from construction_service.model.state_record import DialogueStateRecord  # noqa: F401
    from sqlalchemy.ext.asyncio import create_async_engine

    url = make_url(settings.database_url)
    if url.database != expected_database:
        raise ValueError("Database name does not match --expected-database; no changes made.")
    engine = create_async_engine(url, echo=False, hide_parameters=True)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
    finally:
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-database", required=True,
                        help="Must exactly match the configured dedicated AI database name.")
    args = parser.parse_args()
    asyncio.run(initialize(args.expected_database))
    print("AI state tables ready. Existing data preserved.")


if __name__ == "__main__":
    main()
