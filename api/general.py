from typing import Optional, List

from fastapi import APIRouter, HTTPException, Query
from fastapi import Depends
from fastapi.security import HTTPBearer


from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse

from models.api import responses
from models.database.models import Groups
from database.base import get_session_fastapi, search_group


general_router = APIRouter()
security = HTTPBearer()


@general_router.get("/groups", tags=["Schedules"], responses={200: {"model": List[responses.Groups]}})
async def get_groups(
    group_name: Optional[str] = Query(None, alias="groupName", description="Точное совпадение"),
    group_id: Optional[int] = Query(None, alias="groupId"),
    search_query: Optional[str] = Query(None, alias="searchQuery", description="Поисковой запрос, регистр не важен"),
    session: AsyncSession = Depends(get_session_fastapi),
):
    """
    Без аргументов — все группы
    """
    if search_query is not None:
        return JSONResponse(await search_group(search_query), status_code=200)

    query = select(Groups.id, Groups.name)
    if group_name:
        query = query.where(Groups.name == group_name.upper())
    elif group_id:
        query = query.where(Groups.id == group_id)

    result = await session.execute(query)
    groups_list = [dict(r._mapping) for r in result]

    if not groups_list and (group_name or group_id):
        raise HTTPException(status_code=404, detail="Group not found")

    return JSONResponse(groups_list, status_code=200)


# Joke
@general_router.get("/", response_class=HTMLResponse)
async def rickroll():
    """
    RickRoll если кто-то захочет исследовать api
    """
    return RedirectResponse("https://youtu.be/-cctf5hP900?si=Qm9q8RzFWVyGCKrH&t=466")
