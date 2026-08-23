from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.tag import TagRead
from app.db.models.tag import Tag
class TagCrud:
   def __init__(self, db: AsyncSession) -> None:
        self._db = db
   async def list_all(self, user_id: int) -> list[TagRead]:
    result = await self._db.execute(
            select(Tag).where(Tag.user_id == user_id).order_by(Tag.name)
        )
    tags = result.scalars().all()
    results = []
    for t in tags:
            results.append(TagRead.model_validate(t))
    return results  
     
     