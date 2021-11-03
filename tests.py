import unittest
from main import AccountingMicroservice


# test case for testing methods im microservice class responsible for providing a text representation of the stored data
class MicroserviceDisplayMethods(unittest.TestCase):

    def setUp(self):
        self.microservice = AccountingMicroservice(1, {"USD": 1, "EUR": 1, "RUB": 1})
        self.microservice._rate_dict = {"USD": 2, "EUR": 3}

    def test_currency_balance(self):
        self.assertEqual(self.microservice.currency_balance("USD"), "USD:1")

    def test_all_currencies_balance(self):
        self.assertEqual(self.microservice.all_currencies_balance(), "USD:1\nEUR:1\nRUB:1\n\n")

    def test_calculate_non_rub_rates(self):
        self.assertEqual(self.microservice._calculate_non_rub_rates(), {"EUR-USD": 1.5})

    def test_all_currencies_rates(self):
        self.assertEqual(self.microservice.all_currencies_rates(), "RUB-USD:2\nRUB-EUR:3\nEUR-USD:1.5\n\n")

    def test_total_balance(self):
        self.assertEqual(self.microservice.total_balance(), 'sum: 6 RUB / 3.0 USD / 2.0 EUR')
