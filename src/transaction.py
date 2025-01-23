from config import INCOME


class Transaction:
    def __init__(self, date: str, amount: float, description: str, category: str):
        self.date = date
        self.amount = amount
        self.description = description
        self.category = category if category else ''

        if self.category in INCOME:
            self.amount = -self.amount

    def __str__(self):
        return f'{self.date} {self.category:25s} {self.amount:7.2f} {self.description}'

    def __repr__(self):
        return self.__str__()
