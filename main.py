import asyncio
import logging
from aiohttp import ClientSession, web
import json
import argparse
from microservice import AbstractAccountingMicroservice


class AccountingMicroservice(AbstractAccountingMicroservice):
    def __init__(self, period_minutes: int, balance: dict[str, float]):
        self.__balance = balance
        # RUB to RUB exchange rate is 1 to 1; no need to store it
        self.__rate_dict = {key: 0 for key in balance.keys() if key != "RUB"}
        self.__period_seconds = period_minutes*60

    async def get_exchange_rate_async(self, ):
        """Asynchronously fetches exchange rates from an external API based on keys from rate_dict.
        Stores them as values of rate_dict"""
        async with ClientSession() as session:
            while True:
                async with session.get(r'https://www.cbr-xml-daily.ru/daily_json.js') as response:
                    text: str = await response.text()
                rates = json.loads(text)['Valute']
                for key in self.__rate_dict.keys():
                    self.__rate_dict[key] = rates[key]["Value"]
                await asyncio.sleep(self.__period_seconds)

    def currency_balance(self, currency: str) -> str:
        """Synchronous method to pass the currency balance into the aiohttp-compatible handlers"""
        result_format: str = '{curr}:{bal}'
        if currency.islower():
            currency = currency.upper()
        return result_format.format(curr=currency, bal=self.__balance[currency])

    def all_currencies_balance(self) -> str:
        """Synchronous method to pass the total balance into the aiohttp-compatible handlers"""
        result: str = ""
        for key in self.__balance.keys():
            result += self.currency_balance(key) + '\n'
        result += '\n'
        return result

    def calculate_non_rub_rates(self) -> dict[str, float]:
        """Synchronous methods that calculates non-rub exchange rates as they are not stored"""
        result_dict = {}
        rate_dict = self.__rate_dict.copy()
        for i in range(2):
            popped_currency = rate_dict.popitem()
            for key, value in rate_dict.items():
                rate = 0
                if value != 0:
                    rate = popped_currency[1] / value
                result_dict.update({popped_currency[0] + '-' + key: rate})
        return result_dict

    def all_currencies_rates(self) -> str:
        """Synchronous method to display all the exchange rates (including the non-RUB ones"""
        result: str = ""
        rate_format = '{currencies}:{rate}\n'
        for key, value in self.__rate_dict.items():
            result += rate_format.format(currencies='RUB-' + key, rate=value)

        non_rub_rates = self.calculate_non_rub_rates()
        for key, value in non_rub_rates.items():
            result += rate_format.format(currencies=key, rate=value)

        result += '\n'
        return result


_microservice: AccountingMicroservice = None


async def _currency_balance_get(request: web.Request):
    currency_name: str = request.match_info['name']
    global _microservice
    return web.Response(text=_microservice.currency_balance(currency_name), headers={'content-type': 'text/plain'})


async def _all_currencies_balance_get(request: web.Request):
    global _microservice
    return web.Response(text=_microservice.all_currencies_balance() + _microservice.all_currencies_rates(),
                        headers={'content-type': 'text/plain'})


def main():
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

    global _microservice
    _microservice = AccountingMicroservice(arguments.period, {"USD": arguments.usd, "EUR": arguments.eur,
                                                              "RUB": arguments.rub})
    app = web.Application()
    app.add_routes([web.get(r'/{name:[a-z]{3}}/get', _currency_balance_get),
                    web.get('/amount/get', _all_currencies_balance_get)])
    web.run_app(app, host="localhost", port=8080)


if __name__ == "__main__":
    main()
