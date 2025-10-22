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