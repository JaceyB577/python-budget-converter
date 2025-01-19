import argparse
import csv
import sys

from fuzzywuzzy import fuzz

INCOME = [
    "Employment (Net)",
    "Friend",
    "Interest",
    "Twitch Payout",
    "Lottery Winnings",
    "Birthday"]

CATEGORIES = {
    # Income
    "Employment (Net)": ["SSTL"],
    "Friend": [],
    "Interest": ["INTEREST"],
    "Twitch Payout": [],
    "Lottery Winnings": [],
    "Birthday": [],
    # True Expenses
    "Housing": ["Rent"],
    "Utilities": ["Utilities"],
    "Groceries": ["Groceries", "TESCO STORES"],
    "Transportation": ["Transportation"],
    "Fees": ["CLUB LLOYDS FEE", "CLUB LLOYDS WAIVED"],
    # Expenses
    "Body": ["SURREY SPORTS PARK", "PureGym"],
    "Charity": [],
    "Clothing": [],
    "Days Out": [],
    "Dining Out": ["Toby Carvery", "WELCOME BREAK"],
    "Fun": ["Google Play Apps"],
    "Gift": [],
    "Holiday": [],
    "Lottery": ["NATIONAL LOTTERY"],
    "Parking": ["RINGGO", "WAVERLEY BOROUGH"],
    "Stream": ["EPIDEMICSO", "ADOBESYSTE"],
    "Subscriptions": ["Google YouTubePrem", "LYRA LYRA", "PROPHECY GIRLS POD"],
    "Therapy": ["Kirsty Stacy"],
    "Twitch": ["TWITCHINTE", "PATREON"],
    "Work": [],
    # Savings
    "Emergency Fund": [],
    "Retirement Account": [],
    "Stock Portfolio": [],
    "Sinking Fund Down Payment": [],
    "Sinking Fund Rest": [],
    "Credit Cards": ["National Westminster", "NW MASTERCARD", "SANTANDERCARDS LTD", "B/CARD PLAT VISA"],
    "Decorating": ["DECORATING FUND"],
    "Transfer": [],
}


def get_fuzzy_score(lhs: str, rhs: str) -> int:
    return fuzz.partial_ratio(lhs.lower(), rhs.lower())


def detect_category(description):
    max_score = 0
    cat = ''

    for category in CATEGORIES:
        for desc in CATEGORIES[category]:
            score = get_fuzzy_score(description, desc)

            if score > max_score and score >= 90:
                max_score = score
                cat = category

    return cat


class Transaction:
    def __init__(self, date, amount, description):
        self.date = date
        self.amount = amount
        self.description = description

        self.category = detect_category(self.description)

        if self.category in INCOME:
            self.amount = -self.amount

    def __str__(self):
        return f'{self.date} {self.category:25s} {self.amount:7.2f} {self.description}'

    def __repr__(self):
        return self.__str__()


def parse_csv(csv_filename: str) -> list[list[str]]:
    lines = []

    with open(csv_filename, "r") as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')

        for row in csv_reader:
            lines.append(row)

    lines.reverse()

    return lines


def create_transaction(date: str, amount: int, description: str) -> list[Transaction]:
    transactions = []

    if get_fuzzy_score(description, "Rent") > 90:
        rent = 933.28
        groceries = 155.00
        transportation = 128.55
        utilities = amount - rent - groceries - transportation

        transactions.append(Transaction(date, rent, "Rent"))
        transactions.append(Transaction(date, utilities, "Utilities"))
        transactions.append(Transaction(date, groceries, "Groceries"))
        transactions.append(Transaction(date, transportation, "Transportation"))
    else:
        transactions.append(Transaction(date, amount, description))

    return transactions


def process_lloyds(csv_lines: list[list[str]]) -> list[Transaction]:
    transactions = []

    headers = csv_lines.pop()

    date_idx = headers.index('Transaction Date')
    desc_idx = headers.index('Transaction Description')
    credit_idx = headers.index('Credit Amount')
    debit_idx = headers.index('Debit Amount')

    for row in csv_lines:
        credit = float(row[credit_idx]) if row[credit_idx] else 0
        debit = float(row[debit_idx]) if row[debit_idx] else 0

        transactions.extend(create_transaction(row[date_idx], debit - credit, row[desc_idx]))

    return transactions


def process_natwest(csv_lines: list[list[str]]) -> list[Transaction]:
    pass


def clean_up_transactions(transactions: list[Transaction]) -> list[Transaction]:
    for i in range(0, len(transactions)):
        transaction = transactions[i]

        # Prophecy Girls
        if ((get_fuzzy_score(transaction.description, "NON-GBP TRANS FEE") > 90
             or get_fuzzy_score(transaction.description, "NON-GBP PURCH FEE") > 90)
                and i > 1
                and transactions[i - 1].category == "Subscriptions"):
            transaction.category = "Subscriptions"

    return transactions


def export_to_csv(bank: str, transactions: list[Transaction]):
    file = "export.csv"

    with open(file, "w", newline='', encoding='utf-8') as csv_file:
        csv_writer = csv.writer(csv_file, delimiter=',')

        for transaction in transactions:
            row = [transaction.date,
                   bank,
                   '',  # Type
                   transaction.category,
                   f"{transaction.amount:.2f}",
                   transaction.description]
            csv_writer.writerow(row)


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("-f", "--file")
    parser.add_argument("-b", "--bank", choices=["Lloyds"])
    parser.add_argument("-q", "--quiet", action="store_true")

    args = parser.parse_args()

    lines = parse_csv(args.file)

    match args.bank:
        case "Lloyds":
            transactions = process_lloyds(lines)
        case "Natwest 7051" | "Natwest":
            transactions = process_natwest(lines)
        case _:
            print(f"Unable to locate Bank: {args.bank}")
            sys.exit(1)

    transactions = clean_up_transactions(transactions)

    export_to_csv(args.bank, transactions)


if __name__ == '__main__':
    main()
