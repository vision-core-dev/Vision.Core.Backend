from fastapi import HTTPException


async def _upload_to_bunny(path: str, data: bytes, content_type: str) -> str:
    import httpx
    from os import getenv

    api_key = getenv("BUNNY_STORAGE_API_KEY")
    zone = getenv("BUNNY_STORAGE_ZONE")
    region = getenv("BUNNY_STORAGE_REGION", "storage.bunnycdn.com")
    pull = getenv("BUNNY_PULL_ZONE_HOSTNAME")

    if not api_key or not zone or not pull:
        raise HTTPException(status_code=500, detail="bunnycdn_not_configured")

    url = f"https://{region}/{zone}/{path}"
    headers = {
        "AccessKey": api_key,
        "Content-Type": "application/octet-stream"
    }
    async with httpx.AsyncClient() as client:
        resp = await client.put(url, headers=headers, content=data)
    if resp.status_code >= 400:
        raise HTTPException(status_code=500, detail=f"upload_failed ({resp.status_code})")

# повертаємо URL, доступну для Pull Zone
    return f"https://{pull}/{path}"


from fastapi import UploadFile

# Global progress tracker (in-memory for now, Redis would be better for multi-worker)
UPLOAD_PROGRESS = {}

async def _upload_stream_to_bunny(path: str, temp_file_path: str, content_type: str, upload_id: str = None) -> str:
    """Stream an upload to BunnyCDN from a local file path and report progress if upload_id is provided."""
    import httpx
    from os import getenv

    api_key = getenv("BUNNY_STORAGE_API_KEY")
    zone = getenv("BUNNY_STORAGE_ZONE")
    region = getenv("BUNNY_STORAGE_REGION", "storage.bunnycdn.com")
    pull = getenv("BUNNY_PULL_ZONE_HOSTNAME")

    if not api_key or not zone or not pull:
        raise HTTPException(status_code=500, detail="bunnycdn_not_configured")

    import os
    import asyncio
    
    total_size = os.path.getsize(temp_file_path) if os.path.exists(temp_file_path) else 0
    url = f"https://{region}/{zone}/{path}"
    headers = {
        "AccessKey": api_key,
        "Content-Type": content_type,
        "Content-Length": str(total_size)
    }

    async def file_streamer():
        chunk_size = 1024 * 1024 * 4  # 4 MB chunks
        sent_bytes = 0
        with open(temp_file_path, "rb") as f:
            while True:
                chunk = await asyncio.to_thread(f.read, chunk_size)
                if not chunk:
                    break
                yield chunk
                sent_bytes += len(chunk)
                if upload_id and total_size > 0:
                    UPLOAD_PROGRESS[upload_id] = int((sent_bytes / total_size) * 100)

    try:
        if upload_id:
            UPLOAD_PROGRESS[upload_id] = 0
            
        async with httpx.AsyncClient(timeout=None) as client:
            resp = await client.put(url, headers=headers, content=file_streamer())
    finally:
        if upload_id and upload_id in UPLOAD_PROGRESS:
            del UPLOAD_PROGRESS[upload_id]

    if resp.status_code >= 400:
        raise HTTPException(status_code=500, detail=f"upload_failed ({resp.status_code})")

    return f"https://{pull}/{path}"


async def _delete_from_bunny(path: str):
    import httpx
    from os import getenv

    api_key = getenv("BUNNY_STORAGE_API_KEY")
    zone = getenv("BUNNY_STORAGE_ZONE")
    region = getenv("BUNNY_STORAGE_REGION", "storage.bunnycdn.com")

    if not api_key or not zone:
        raise HTTPException(status_code=500, detail="bunnycdn_not_configured")

    url = f"https://{region}/{zone}/{path}"
    headers = {
        "AccessKey": api_key
    }
    async with httpx.AsyncClient() as client:
        resp = await client.delete(url, headers=headers)
    if resp.status_code >= 400:
        raise HTTPException(status_code=500, detail=f"delete_failed ({resp.status_code})")