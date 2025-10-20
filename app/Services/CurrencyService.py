import os
import json
import httpx
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class CurrencyService:
    def __init__(self):
        self.exchange_api_key = os.getenv("EXCHANGE_RATE_API_URL")
        self.cache_ttl = 60 * 60 * 6  # 🕐 6 годин кешування

    async def GetExchangeRate(self, currency_code: str) -> dict:
        """
        📈 Отримати обмінний курс для заданої валюти з API.
        """
        async with httpx.AsyncClient() as client:
            url = f"https://v6.exchangerate-api.com/v6/{self.exchange_api_key}/latest/{currency_code}"
            response = await client.get(url)
            data = response.json()

            if data.get("result") != "success":
                raise ValueError("❌ Не вдалося отримати обмінний курс")

            return data["conversion_rates"]

    async def GetCachedExchangeRate(self, redis, currency_code: str) -> dict:
        """
        📦 Отримати обмінний курс з кешу (якщо є), або запросити заново.
        """
        cache_key = f"exchange:{currency_code.upper()}"
        cached = await redis.get(cache_key)

        if cached:
            return json.loads(cached)

        # 🆕 Якщо нема кешу — тягнемо з API і кешуємо
        rates = await self.GetExchangeRate(currency_code)
        await redis.setex(cache_key, self.cache_ttl, json.dumps(rates))
        return rates

    async def RefreshExchangeRate(self, redis, currency_code: str) -> dict:
        """
        🔄 Оновити кеш курсу валюти вручну.
        """
        cache_key = f"exchange:{currency_code.upper()}"
        rates = await self.GetExchangeRate(currency_code)
        await redis.setex(cache_key, self.cache_ttl, json.dumps(rates))
        print(f"✅ Курс {currency_code.upper()} оновлено о {datetime.now()}")
        return rates

    async def Convert(self, redis, from_currency: str, to_currency: str, amount: float) -> float:
        """
        💱 Конвертувати суму з однієї валюти в іншу.
        """
        rates = await self.GetCachedExchangeRate(redis, from_currency)
        if to_currency.upper() not in rates:
            raise ValueError("❌ Валюта не знайдена у списку курсів")
        return round(amount * rates[to_currency.upper()], 2)
