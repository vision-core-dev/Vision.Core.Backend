import uuid
from typing import List

from fastapi import UploadFile, File, Depends, APIRouter, HTTPException

from app.Infrastructure.Storage import _upload_to_bunny
from app.Objects.UserModel import User
from app.Services.Hub.AuthService.depends import getuser

upload_router = APIRouter(prefix="/Uploads", tags=["Uploads"])

# Maximum file size: 50MB
MAX_FILE_SIZE = 50 * 1024 * 1024
# Allowed file types (MIME types)
ALLOWED_TYPES = {
    # Images
    "image/jpeg", "image/png", "image/gif", "image/webp", "image/svg+xml",
    # Documents
    "application/pdf", "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-powerpoint",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    # Text
    "text/plain", "text/csv", "text/html", "text/markdown",
    # Archives
    "application/zip", "application/x-rar-compressed", "application/x-7z-compressed",
    # Audio
    "audio/mpeg", "audio/wav", "audio/webm", "audio/ogg", "audio/mp4",
    # Video
    "video/mp4", "video/webm", "video/ogg", "video/quicktime",
    # Other
    "application/json", "application/xml",
}


@upload_router.post("/Image")
async def upload_image(
    file: UploadFile = File(...),
    user: User = Depends(getuser)
):
    """Завантажити одне зображення"""
    contents = await file.read()
    filename = f"uploads/{user.id}_{uuid.uuid4()}_{file.filename}"

    file_url = await _upload_to_bunny(filename, contents, file.content_type)

    return {"file_url": file_url}


@upload_router.post("/Chat")
async def upload_chat_files(
    files: List[UploadFile] = File(...),
    user: User = Depends(getuser)
):
    """
    Завантажити файли для чату.
    Підтримує: зображення, документи, аудіо, відео.
    Максимальний розмір: 50MB на файл.
    """
    uploaded_urls = []
    errors = []

    for file in files:
        try:
            # Validate content type
            if file.content_type and file.content_type not in ALLOWED_TYPES:
                errors.append({
                    "filename": file.filename,
                    "error": f"Unsupported file type: {file.content_type}"
                })
                continue

            # Read file contents
            contents = await file.read()

            # Validate file size
            if len(contents) > MAX_FILE_SIZE:
                errors.append({
                    "filename": file.filename,
                    "error": f"File too large. Maximum size is {MAX_FILE_SIZE // (1024 * 1024)}MB"
                })
                continue

            # Generate unique filename
            ext = file.filename.split(".")[-1] if "." in file.filename else ""
            unique_name = f"{uuid.uuid4()}.{ext}" if ext else str(uuid.uuid4())
            filename = f"chat/{user.id}/{unique_name}"

            # Upload to storage
            file_url = await _upload_to_bunny(filename, contents, file.content_type or "application/octet-stream")
            uploaded_urls.append(file_url)

        except Exception as e:
            errors.append({
                "filename": file.filename,
                "error": str(e)
            })

    if not uploaded_urls and errors:
        raise HTTPException(status_code=400, detail={"message": "All files failed to upload", "errors": errors})

    return {
        "urls": uploaded_urls,
        "count": len(uploaded_urls),
        "errors": errors if errors else None
    }


@upload_router.post("/Voice")
async def upload_voice_message(
    file: UploadFile = File(...),
    user: User = Depends(getuser)
):
    """
    Завантажити голосове повідомлення.
    Підтримує: audio/webm, audio/ogg, audio/mp4, audio/mpeg
    """
    # Validate audio type
    allowed_audio = {"audio/webm", "audio/ogg", "audio/mp4", "audio/mpeg", "audio/wav"}
    if file.content_type and file.content_type not in allowed_audio:
        raise HTTPException(status_code=400, detail=f"Unsupported audio type: {file.content_type}")

    contents = await file.read()

    # Validate size (10MB max for voice)
    max_voice_size = 10 * 1024 * 1024
    if len(contents) > max_voice_size:
        raise HTTPException(status_code=400, detail=f"Voice message too large. Maximum size is 10MB")

    # Generate filename
    ext = "webm"
    if file.content_type:
        ext = file.content_type.split("/")[-1]
    unique_name = f"{uuid.uuid4()}.{ext}"
    filename = f"voice/{user.id}/{unique_name}"

    file_url = await _upload_to_bunny(filename, contents, file.content_type or "audio/webm")

    return {"url": file_url}