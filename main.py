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

    def all_currencies_rates(self) -> str:
        """Synchronous method to display all the exchange rates (including the non-RUB ones"""
        result: str = ""
        rate_format = '{currencies}:{rate}\n'
        for key, value in self.__rate_dict.items():
            result += rate_format.format(currencies='RUB-' + key, rate=value)

        #rates for non-rub exchanges are calculated here
        non_rub_rates = ''
        # copy needed because the dictionary will have to be popped in the code below to get non-rub rates
        rate_dict = self.__rate_dict.copy()
        popped_currency = rate_dict.popitem()
        for key, value in rate_dict.items():
            rate = 0
            if value != 0:
                rate = popped_currency[1] / value
            non_rub_rates += rate_format.format(currencies=popped_currency[0] + '-' + key,
                                                rate=rate)
        popped_currency = rate_dict.popitem()
        if rate_dict:
            for key, value in rate_dict.items():
                rate = 0
                if value != 0:
                    rate = popped_currency[1] / value
                non_rub_rates += rate_format.format(currencies=popped_currency[0] + '-' + key,
                                                    rate=rate)

        result += non_rub_rates + '\n'
        return result


microservice: AccountingMicroservice = None


async def currency_balance_get(request: web.Request):
    currency_name: str = request.match_info['name']
    global microservice
    return web.Response(text=microservice.currency_balance(currency_name), headers={'content-type': 'text/plain'})


async def all_currencies_balance_get(request: web.Request):
    global microservice
    return web.Response(text=microservice.all_currencies_balance() + microservice.all_currencies_rates(),
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

    global microservice
    microservice = AccountingMicroservice(arguments.period, {"USD": arguments.usd, "EUR": arguments.eur,
                                                             "RUB": arguments.rub})
    app = web.Application()
    app.add_routes([web.get(r'/{name:[a-z]{3}}/get', currency_balance_get),
                    web.get('/amount/get', all_currencies_balance_get)])
    web.run_app(app, host="localhost", port=8080)


if __name__ == "__main__":
    main()
