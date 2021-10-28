import requests
import asyncio
import logging
import aiohttp
import json
import argparse
from microservice import AbstractAccountingMicroservice


class AccountingMicroservice(AbstractAccountingMicroservice):

    def __init__(self, currency1: str = "USD", currency2: str = "EUR", currency3: str = "RUB"):
        self.rate_dict = {currency1: 0, currency2: 0, currency3: 0}

    async def get_exchange_rate_async(self):
        async with aiohttp.ClientSession() as session:
            async with session.get(r'https://www.cbr-xml-daily.ru/daily_json.js') as response:
                text: str = await response.text()
                rates = json.loads(text)['Valute']
                for key in self.rate_dict.keys():
                    self.rate_dict[key] = rates[key]["Value"]
        #response = requests.get(r'https://www.cbr-xml-daily.ru/daily_json.js')
        #rate_dict = await json.loads(response.text)['Valute']


async def main():
    app = AccountingMicroservice("USD", "EUR", "GBP")
    await app.get_exchange_rate_async()
    print("debug")


if __name__ == "__main__":
    asyncio.run(main())
