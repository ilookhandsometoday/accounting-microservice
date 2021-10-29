import requests
import asyncio
import logging
import aiohttp
import json
import argparse
from microservice import AbstractAccountingMicroservice


class AccountingMicroservice(AbstractAccountingMicroservice):

    def __init__(self, period: int, balance: dict[str, float]):
        self.balance = balance
        self.rate_dict = {key: 0 for key in balance.keys() if key != "RUB"}
        self.period = period

    async def get_exchange_rate_async(self):
        async with aiohttp.ClientSession() as session:
            while True:
                async with session.get(r'https://www.cbr-xml-daily.ru/daily_json.js') as response:
                    text: str = await response.text()
                rates = json.loads(text)['Valute']
                for key in self.rate_dict.keys():
                    self.rate_dict[key] = rates[key]["Value"]
                print(self.rate_dict)
                await asyncio.sleep(self.period)
        #response = requests.get(r'https://www.cbr-xml-daily.ru/daily_json.js')
        #rate_dict = await json.loads(response.text)['Valute']


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--period", action="store", default=5, type=int, required=False, help="period in minutes",
                        metavar="N")
    parser.add_argument("--usd", action="store", default=0, type=float, required=False, help="starting balance of USD",
                        metavar="X")
    parser.add_argument("--eur", action="store", default=0, type=float, required=False, help="starting balance of EUR",
                        metavar="X")
    parser.add_argument("--rub", action="store", default=0, type=float, required=False, help="starting balance of RUB",
                        metavar="X")
    arguments = parser.parse_args()
    microservice = AccountingMicroservice(arguments.period * 60, {"USD": arguments.usd, "EUR": arguments.eur,
                                                                  "RUB": arguments.rub})
    await microservice.get_exchange_rate_async()
    print("debug")


if __name__ == "__main__":
    asyncio.run(main())
