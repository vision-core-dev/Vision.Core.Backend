from fastapi import APIRouter

hub_router = APIRouter(prefix="/Hub")

from .Auth import auth_router
hub_router.include_router(auth_router)

from .Users import users_router
hub_router.include_router(users_router)

from .Events import events_router
hub_router.include_router(events_router)

from .UserMe import user_me_router
hub_router.include_router(user_me_router)

from app.API.HUB.Users.UserRoles import user_roles_router
hub_router.include_router(user_roles_router)

from .Boards import boards_router
hub_router.include_router(boards_router)

from .Knowledge import knowledge_router
hub_router.include_router(knowledge_router)

from .Tasks import tasks_router
hub_router.include_router(tasks_router)

from .Uploads import upload_router
hub_router.include_router(upload_router)

from .Finance import finance_router
hub_router.include_router(finance_router)

from .VisionBot import vision_bot_router
hub_router.include_router(vision_bot_router)

from  .forms import forms_router
hub_router.include_router(forms_router)

from .Logs import router as logs_router
hub_router.include_router(logs_router)

from .online_websocket import online_ws_router
hub_router.include_router(online_ws_router)

from .OrgStructure import org_structure_router
hub_router.include_router(org_structure_router)

from .Chat import chat_router
hub_router.include_router(chat_router)

from .chat_websocket import chat_ws_router
hub_router.include_router(chat_ws_router)