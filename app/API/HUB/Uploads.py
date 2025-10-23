import uuid

from fastapi import UploadFile, File, Depends, APIRouter

from app.Infrastructure.Storage import _upload_to_bunny
from app.Objects.UserModel import User
from app.Services.Hub.AuthService.depends import getuser

upload_router = APIRouter()

@upload_router.post("/UploadImage")
async def upload_file(
    file: UploadFile = File(...),
    user: User = Depends(getuser)
):
    contents = await file.read()
    filename = f"uploads/{user.id}_{uuid.uuid4()}_{file.filename}"

    # викликаємо Bunny upload
    file_url = await _upload_to_bunny(filename, contents, file.content_type)

    return {"file_url": file_url}