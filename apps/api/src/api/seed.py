import asyncio
from datetime import date

from sqlalchemy import select

from api.db import async_session
from api.models import Seminar

SEMINARS = [
    {"name": "中村ゼミ", "capacity": 10},
    {"name": "福原ゼミ", "capacity": 8},
]


async def seed_seminars() -> None:
    async with async_session() as session:
        result = await session.execute(select(Seminar.name))
        existing_names = set(result.scalars().all())

        created = 0
        for data in SEMINARS:
            if data["name"] in existing_names:
                continue
            session.add(
                Seminar(
                    name=data["name"],
                    capacity=data["capacity"],
                    recruitment_start=date(2026, 4, 1),
                    recruitment_end=date(2026, 5, 1),
                )
            )
            created += 1
        await session.commit()

    skipped = len(SEMINARS) - created
    print(f"Seeded {created} seminar(s), skipped {skipped} already-existing.")


def main() -> None:
    asyncio.run(seed_seminars())


if __name__ == "__main__":
    main()
