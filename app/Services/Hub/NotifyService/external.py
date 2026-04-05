import os
import httpx

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
DISCORD_BOT_WEBHOOK_URL = os.getenv("DISCORD_NOTIFY_WEBHOOK_URL", "")


async def send_telegram_notification(chat_id: str, title: str, message: str, link: str | None = None):
    if not TELEGRAM_BOT_TOKEN or not chat_id:
        return

    text = f"<b>{title}</b>\n{_strip_html(message)}"
    if link:
        base_url = os.getenv("FRONTEND_URL", "https://hub.visioncore.dev")
        text += f"\n\n<a href=\"{base_url}{link}\">Відкрити</a>"

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        async with httpx.AsyncClient() as client:
            await client.post(url, json={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            })
    except Exception:
        pass


async def send_discord_notification(discord_id: str, title: str, message: str, link: str | None = None):
    bot_token = os.getenv("DISCORD_BOT_TOKEN", "")
    if not bot_token or not discord_id:
        return

    # Open DM channel with user
    try:
        async with httpx.AsyncClient() as client:
            dm_res = await client.post(
                "https://discord.com/api/v10/users/@me/channels",
                json={"recipient_id": discord_id},
                headers={"Authorization": f"Bot {bot_token}"},
            )
            if dm_res.status_code != 200:
                return
            channel_id = dm_res.json()["id"]

            base_url = os.getenv("FRONTEND_URL", "https://hub.visioncore.dev")
            description = _strip_html(message)
            if link:
                description += f"\n\n[Відкрити]({base_url}{link})"

            await client.post(
                f"https://discord.com/api/v10/channels/{channel_id}/messages",
                json={
                    "embeds": [{
                        "title": title,
                        "description": description,
                        "color": 0x7C3AED,
                    }]
                },
                headers={"Authorization": f"Bot {bot_token}"},
            )
    except Exception:
        pass


def _strip_html(text: str) -> str:
    import re
    return re.sub(r"<[^>]+>", "", text)
