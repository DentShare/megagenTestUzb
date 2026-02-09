from sqlalchemy import or_
from typing import List
from database.models import Clinic
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

async def search_clinics(session: AsyncSession, query: str, limit: int = 50) -> List[Clinic]:
    """
    Search clinics by name, doctor_name, or phone_number.
    Case-insensitive search with limit for performance.
    """
    # Use ILIKE for case-insensitive partial match
    search_pattern = f"%{query}%"
    stmt = (
        select(Clinic)
        .where(
            or_(
                Clinic.name.ilike(search_pattern),
                Clinic.doctor_name.ilike(search_pattern),
                Clinic.phone_number.ilike(search_pattern)
            )
        )
        .limit(limit)  # Ограничиваем результаты для производительности
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())
