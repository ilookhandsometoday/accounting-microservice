import asyncio
import logging
from aiohttp import ClientSession, web
import json
import argparse
from microservice import AbstractAccountingMicroservice


class AccountingMicroservice(AbstractAccountingMicroservice):
    def __init__(self, period_minutes: int, balance: dict[str, float]):
        """Warning: for proper functionality keys of variable balance should contain capitalized
        abbreviations of currency names, e.g. USD"""
        self._balance = balance
        # RUB to RUB exchange rate is 1 to 1; no need to store it
        self._rate_dict = {key: 0 for key in balance.keys() if key != "RUB"}
        self._period_seconds = period_minutes * 60

    async def get_exchange_rate_async(self):
        """Asynchronously fetches exchange rates from an external API based on keys from rate_dict.
        Stores them as values of rate_dict"""
        cancelled = False
        async with ClientSession() as session:
            while not cancelled:
                try:
                    async with session.get(r'https://www.cbr-xml-daily.ru/daily_json.js') as response:
                        text: str = await response.text()
                    rates = json.loads(text)['Valute']
                    for key in self._rate_dict.keys():
                        self._rate_dict[key] = rates[key]["Value"]
                    await asyncio.sleep(self._period_seconds)
                except asyncio.CancelledError:
                    cancelled = True

    def currency_balance(self, currency: str) -> str:
        """Synchronous method to pass the currency balance into the aiohttp-compatible handlers"""
        result_format: str = '{curr}:{bal}'
        if currency.islower():
            currency = currency.upper()
        return result_format.format(curr=currency, bal=self._balance[currency])

    def all_currencies_balance(self) -> str:
        """Synchronous method to pass the balance of each currency into the aiohttp-compatible handlers"""
        result: str = ""
        for key in self._balance.keys():
            result += self.currency_balance(key) + '\n'
        result += '\n'
        return result

    def calculate_non_rub_rates(self) -> dict[str, float]:
        """Synchronous methods that calculates non-rub exchange rates as they are not stored"""
        result_dict = {}
        rate_dict = self._rate_dict.copy()
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
        for key, value in self._rate_dict.items():
            result += rate_format.format(currencies='RUB-' + key, rate=value)

        non_rub_rates = self.calculate_non_rub_rates()
        for key, value in non_rub_rates.items():
            result += rate_format.format(currencies=key, rate=value)

        result += '\n'
        return result

    def total_balance(self) -> str:
        total_balance_rub = 0
        for key, value in self._balance.items():
            if key != "RUB":
                total_balance_rub += value * self._rate_dict[key]
            else:
                total_balance_rub += value
        total_balance_dict: dict[str, str] = {"RUB": str(total_balance_rub) + " RUB"}

        for key, value in self._rate_dict.items():
            total_balance_dict.update({key: str(total_balance_rub / value) + " " + key})
        result: str = "sum: "
        for index, value in enumerate(total_balance_dict.values(), start=1):
            if index == 1:
                result += value
            else:
                result += " / " + value
        return result

    def set_amount(self, balance_dict: dict[str, float]):
        """Synchronous function to set amount from payload. Returns True if setting is successful"""
        # Preventing illegal currency names in payload
        if all([(key in self._balance.keys()) for key in balance_dict.keys()]):
            for key in balance_dict.keys():
                # the specified format in which payload is sent is {"usd":10}, so keys have to be made upper case
                key_upper = key.upper()
                if key_upper in self._balance:
                    self._balance[key_upper] = balance_dict[key]
            return True
        else:
            return False

    def modify_amount(self, modification_dict: dict[str, float]):
        """Synchronous function to modify amount from payload. Returns True if modification is successful"""
        # Preventing illegal currency names in payload
        if all([(key in self._balance.keys()) for key in modification_dict.keys()]):
            for key in modification_dict.keys():
                # the specified format in which payload is sent is {"usd":10}, so keys have to be made upper case
                key_upper = key.upper()
                if key_upper in self._balance:
                    self._balance[key_upper] += modification_dict[key]
            return True
        else:
            return False


async def _modify_amount(request: web.Request):
    microservice: AccountingMicroservice = request.app['microservice_instance']
    body: dict[str, float] = await request.json()
    modification_successful = microservice.modify_amount(body)
    if modification_successful:
        return web.Response(text="Amount modified successfully!", headers={'content-type': 'text/plain'})
    else:
        return web.Response(text="Amount modified failed!r", headers={'content-type': 'text/plain'}, status=422)


async def _set_amount(request: web.Request):
    microservice: AccountingMicroservice = request.app['microservice_instance']
    body: dict[str, float] = await request.json()
    setting_successful = microservice.set_amount(body)
    if setting_successful:
        return web.Response(text="Amount set successfully!", headers={'content-type': 'text/plain'})
    else:
        return web.Response(text="Amount set failed!", headers={'content-type': 'text/plain'}, status=422)


async def _currency_balance_get(request: web.Request):
    currency_name: str = request.match_info['name']
    microservice: AccountingMicroservice = request.app['microservice_instance']
    return web.Response(text=microservice.currency_balance(currency_name), headers={'content-type': 'text/plain'})


async def _all_currencies_balance_get(request: web.Request):
    microservice: AccountingMicroservice = request.app['microservice_instance']
    return web.Response(text=microservice.all_currencies_balance() + microservice.all_currencies_rates() +
                        microservice.total_balance(), headers={'content-type': 'text/plain'})


async def _start_background_tasks(app):
    microservice: AccountingMicroservice = app['microservice_instance']
    app['rate_fetch'] = asyncio.create_task(microservice.get_exchange_rate_async())


async def _on_server_shutdown(app):
    app['rate_fetch'].cancel()
    await app['rate_fetch']
    # prevents ugly error messages on app shutdown caused by flaws in asyncio implementation
    await asyncio.sleep(0.1)


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

    microservice = AccountingMicroservice(arguments.period, {"USD": arguments.usd, "EUR": arguments.eur,
                                                             "RUB": arguments.rub})
    app = web.Application()
    app['microservice_instance'] = microservice
    app.on_startup.append(_start_background_tasks)
    app.on_shutdown.append(_on_server_shutdown)
    app.add_routes([web.get(r'/{name:[a-z]{3}}/get', _currency_balance_get),
                    web.get('/amount/get', _all_currencies_balance_get),
                    web.post('/amount/set', _set_amount),
                    web.post('/modify', _modify_amount)])
    web.run_app(app, host="localhost", port=8080)


if __name__ == "__main__":
    main()
