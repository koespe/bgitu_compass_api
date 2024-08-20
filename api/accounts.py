import datetime
import random
import string
from typing import Optional

import aiohttp
from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.encoders import jsonable_encoder
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.responses import JSONResponse

from config import HOSTNAME_PORT, DEFAULT_TIMEZONE
from database.base import get_session_fastapi
from locals import loc
from models.api import payloads, responses
from models.database.models import Accounts, Groups

accounts_router = APIRouter(tags=['Новая авторизация'], prefix='/account')
security = HTTPBearer()


def generate_token(token_type: str):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(64))


@accounts_router.post('/registerGuest',
                      responses={
                          200: {"model": responses.RegisterGuest}
                      })
async def register_guest(payload: payloads.RegisterGuest,
                         session: AsyncSession = Depends(get_session_fastapi)):
    """
    Добавление неподтвержденного пользователя (без аутентификации через EOS)
    """
    access_token = generate_token(token_type='access')
    refresh_token = generate_token(token_type='refresh')

    if payload.groupName == "":
        query = select(Groups.name).where(Groups.id == payload.groupId)
        group_name = await session.scalar(query)
    else:
        group_name = payload.groupName

    find_user_query = select(Accounts).where(Accounts.appUUID == payload.appUUID)
    user_data = await session.scalar(find_user_query)
    if user_data:
        await session.delete(user_data)
        await session.commit()
    token_expire_at = (datetime.datetime.now(DEFAULT_TIMEZONE) +
                       datetime.timedelta(weeks=4)).strftime('%Y-%m-%dT%H:%M:%S.%fZ')
    new_user = Accounts(appUUID=payload.appUUID,
                        groupId=payload.groupId,
                        groupName=group_name,
                        accessToken=access_token,
                        refreshToken=refresh_token,
                        tokenExpireAt=token_expire_at)
    session.add(new_user)
    await session.commit()
    await session.refresh(new_user)
    user_credentials = responses.Credentials(accessToken=access_token,
                                             refreshToken=refresh_token,
                                             expirationDate=token_expire_at)
    response_data = responses.RegisterGuest(userId=new_user.id,
                                            groupId=new_user.groupId,
                                            groupName=group_name,
                                            credentials=user_credentials)
    return response_data


@accounts_router.post('/registerEosUser',
                      responses={
                          200: {"model": responses.RegisterGuest}
                      })
async def register_eos_user(payload: payloads.RegisterEosUser,
                            session: AsyncSession = Depends(get_session_fastapi)):
    eos_group_name = payload.eosGroupName.upper()

    # Генерируем заранее, так как токен сейчас — заглушка перед нормальным JWT
    access_token = generate_token(token_type='access')
    refresh_token = generate_token(token_type='refresh')
    token_expire_at = (datetime.datetime.now(DEFAULT_TIMEZONE) +
                       datetime.timedelta(weeks=4)).strftime('%Y-%m-%dT%H:%M:%S.%fZ')

    # Если пользователь уже есть в БД, то это нужно обработать чтобы не получить IntegrityError
    find_user_query = select(Accounts).where(Accounts.eosUserId == payload.eosUserId)
    user_data = await session.scalar(find_user_query)
    is_user_exist = True if user_data is not None else False

    # Verification (guest -> eosVerified)
    if payload.userId:
        # Обновляем данные, не удаляя их.
        find_user_query = select(Accounts).where(Accounts.id == payload.userId)
        user_data: Accounts = await session.scalar(find_user_query)
        user_data.eosUserId = payload.eosUserId
        user_data.eosGroupName = payload.eosGroupName
        user_data.fullName = payload.fullName
        user_data.avatarUrl = payload.avatarUrl.__str__()

        user_data.accessToken = access_token
        user_data.refreshToken = refresh_token
        user_data.tokenExpireAt = token_expire_at

        # Ищем совпадение по группе
        async with aiohttp.ClientSession() as aiohttp_session:
            req_group_id = await aiohttp_session.get(url=HOSTNAME_PORT + '/groups' + '?groupName=' + eos_group_name)
            if req_group_id.status == 404:
                group_name = None
                group_id = None
            else:
                group_name = eos_group_name
                group_id = (await req_group_id.json()).get('groupId')
        user_data.groupName = group_name
        user_data.groupId = group_id
        await session.commit()

        user_credentials = responses.Credentials(accessToken=access_token,
                                                 refreshToken=refresh_token,
                                                 expirationDate=token_expire_at)
        response_data = responses.RegisterEosUser(userId=payload.userId,
                                                  eosUserId=payload.eosUserId,
                                                  groupId=group_id,
                                                  groupName=group_name,
                                                  credentials=user_credentials)
        return JSONResponse(content=jsonable_encoder(response_data), status_code=200)

    elif is_user_exist:
        # Сохраняем готовые данные
        group_name = user_data.groupName
        group_id = user_data.groupId
        await session.delete(user_data)
        await session.commit()
    else:
        async with aiohttp.ClientSession() as aiohttp_session:
            req_group_id = await aiohttp_session.get(url=HOSTNAME_PORT + '/groups' + '?groupName=' + eos_group_name)
            if req_group_id.status == 404:
                group_name = None
                group_id = None
            else:
                group_name = eos_group_name
                group_id = (await req_group_id.json()).get('groupId')

    new_user = Accounts(eosUserId=payload.eosUserId,
                        groupId=group_id,
                        groupName=group_name,
                        eosGroupName=eos_group_name,
                        fullName=payload.fullName,
                        avatarUrl=payload.avatarUrl.__str__(),
                        accessToken=access_token,
                        refreshToken=refresh_token,
                        tokenExpireAt=token_expire_at)
    session.add(new_user)
    await session.commit()

    await session.refresh(new_user)
    user_credentials = responses.Credentials(accessToken=access_token,
                                             refreshToken=refresh_token,
                                             expirationDate=token_expire_at)
    response_data = responses.RegisterEosUser(userId=new_user.id,
                                              eosUserId=new_user.eosUserId,
                                              groupId=group_id,
                                              groupName=group_name,
                                              credentials=user_credentials)

    # jsonable_encoder без проблем переваривает Pydantic Models
    return JSONResponse(content=jsonable_encoder(response_data), status_code=200)


@accounts_router.put('/chooseGroup',
                     responses={
                         200: {"description": "Группа подтверждена"},
                         404: {"description": "Пользователь не найден"}
                     })
async def handle_different_eosgroupname(payload: payloads.DifferentEosGroupName,
                                        session: AsyncSession = Depends(get_session_fastapi),
                                        credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Случай, когда при авторизации через EOS мы не нашли точного совпадения по названию группы.
    Убираем None: groupId, groupName
    """
    access_token = credentials.credentials

    user_data_query = select(Accounts).where(Accounts.accessToken == access_token)
    user_data = await session.scalar(user_data_query)
    if user_data is not None:
        user_data.groupId = payload.groupId
        user_data.groupName = payload.groupName
        await session.commit()
        return Response(status_code=200)
    else:
        raise HTTPException(status_code=404)


@accounts_router.post('/registerCMT',
                      responses={
                          200: {"description": "OK"},
                          400: {"description": loc('errors', 'no_action')},
                          404: {"description": loc('errors', 'invalid_token')}
                      })
async def register_cmt_token(payload: payloads.CMTokens,
                             credentials: HTTPAuthorizationCredentials = Depends(security),
                             session: AsyncSession = Depends(get_session_fastapi)):
    """
    type: "GMS / HMS "
    """
    access_token = credentials.credentials
    token_type = payload.tokenType
    token = payload.token
    query = await session.execute(select(Accounts).where(Accounts.accessToken == access_token))
    user = query.scalar()
    if user is not None:
        if token_type == 'GMS':
            user.firebaseToken = token
        elif token_type == 'HMS':
            user.hmsToken = token
        else:
            raise HTTPException(detail=loc('errors', 'no_action'), status_code=400)
        await session.commit()
        return Response(status_code=200)
    else:
        raise HTTPException(detail=loc('errors', 'invalid_token'), status_code=404)


@accounts_router.get('/',
                     responses={
                         200: {"model": responses.AccountData},
                         404: {"description": loc('errors', 'invalid_token')}
                     })
async def get_account_data(appUUID: Optional[str] = None,
                           credentials: HTTPAuthorizationCredentials = Depends(security),
                           session: AsyncSession = Depends(get_session_fastapi)):
    """
    appUUID (Optional) для автоматического поиска аккаунта по устройству пользователя
    """
    if appUUID is not None:
        user_data_query = select(Accounts).where(Accounts.appUUID == appUUID)
    else:
        access_token = credentials.credentials
        user_data_query = select(Accounts).where(Accounts.accessToken == access_token)
    user_data: Accounts = await session.scalar(user_data_query)
    if user_data is not None:
        user_data_response = responses.AccountData(userId=user_data.id,
                                                   eosUserId=user_data.eosUserId,
                                                   groupId=user_data.groupId,
                                                   groupName=user_data.groupName,
                                                   fullName=user_data.fullName,
                                                   avatarUrl=user_data.avatarUrl,
                                                   role=user_data.role,
                                                   permissions=user_data.permissions,
                                                   additionalData=user_data.additionalData
                                                   )
        return JSONResponse(content=jsonable_encoder(user_data_response), status_code=200)
    else:
        raise HTTPException(detail=loc('errors', 'invalid_token'), status_code=404)


@accounts_router.post('/updateUUID',
                      responses={
                          200: {"model": responses.UpdateUUID},
                          404: {"description": loc('errors', 'invalid_token')}
                      })
async def update_uuid(new_appUUID: str,
                      credentials: HTTPAuthorizationCredentials = Depends(security),
                      session: AsyncSession = Depends(get_session_fastapi)
                      ):
    """
    В новом обновлении решили сделать UUID который не будет меняться при каждом обновлении, а старый нужно обновить чтобы не создать проблем
    """
    query = select(Accounts).where(Accounts.accessToken == credentials.credentials)
    user_data: Accounts = await session.scalar(query)
    if user_data is not None:
        user_data.appUUID = new_appUUID
        await session.commit()
        user_data_response = responses.UpdateUUID(user_id=user_data.id)
        return JSONResponse(content=jsonable_encoder(user_data_response), status_code=200)
    else:
        raise HTTPException(detail=loc('errors', 'invalid_token'), status_code=404)

