from abc import ABC, abstractmethod


class AbstractAccountingMicroservice(ABC):

    @abstractmethod
    async def get_exchange_rate_async(self):
        pass


def main():
    pass


if __name__ == "__main__":
    main()
