import argparse
import csv
import sys

from fuzzywuzzy import fuzz

from config import CATEGORIES, BILLS_CATEGORIES
from transaction import Transaction


def get_fuzzy_score(lhs: str, rhs: str) -> int:
    return fuzz.partial_ratio(lhs.lower(), rhs.lower())


def detect_category(description, categories: dict[str, list[str]] = None):
    if categories is None:
        categories = CATEGORIES

    max_score = 0
    cat = None

    if "PETROL" in description:
        return "Petrol"

    for category in categories:
        for desc in categories[category]:
            score = get_fuzzy_score(description, desc)

            if score > max_score and score >= 90:
                max_score = score
                cat = category

    return cat


def parse_csv(csv_filename: str) -> list[list[str]]:
    lines = []

    with open(csv_filename, "r", encoding="utf-8") as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')

        for row in csv_reader:
            lines.append(row)

    return lines


def create_transaction(date: str, amount: float, description: str, category: str = None) -> Transaction:
    if category is None:
        category = detect_category(description)

    return Transaction(date, amount, description, category)


def process_lloyds(csv_lines: list[list[str]]) -> list[Transaction]:
    transactions = []

    headers = csv_lines.pop(0)

    csv_lines.reverse()

    date_idx = headers.index('Transaction Date')
    desc_idx = headers.index('Transaction Description')
    credit_idx = headers.index('Credit Amount')
    debit_idx = headers.index('Debit Amount')

    for row in csv_lines:
        date = row[date_idx]
        desc = row[desc_idx]
        credit = float(row[credit_idx]) if row[credit_idx] else 0
        debit = float(row[debit_idx]) if row[debit_idx] else 0
        amount = debit - credit

        if get_fuzzy_score(desc, "Rent") > 90:
            rent = 933.28
            groceries = 151.78
            transportation = 194.79
            utilities = amount - rent - groceries - transportation

            transactions.append(create_transaction(date, rent, "Rent", "Housing"))
            transactions.append(create_transaction(date, utilities, "Utilities", "Utilities"))
            transactions.append(create_transaction(date, groceries, "Groceries", "Groceries"))
            transactions.append(create_transaction(date, transportation, "Transportation", "Transportation"))
        else:
            transactions.append(create_transaction(row[date_idx], debit - credit, row[desc_idx]))

    return transactions


def process_natwest(csv_lines: list[list[str]]) -> list[Transaction]:
    transactions = []

    headers = csv_lines.pop(0)

    csv_lines.reverse()

    date_idx = headers.index('Date')
    desc_idx = headers.index('Description')
    amount_idx = headers.index('Value')

    for row in csv_lines:
        date = row[date_idx]
        desc = row[desc_idx]
        amount = float(row[amount_idx]) if row[amount_idx] else 0

        category = detect_category(desc, BILLS_CATEGORIES)

        transactions.append(create_transaction(date, -amount, desc, category))

    return transactions


def process_monzo(csv_lines: list[list[str]]) -> list[Transaction]:
    transactions: list[Transaction] = []

    headers = csv_lines.pop(0)

    date_idx = headers.index('Date')
    desc_idx = headers.index('Name')
    category_idx = headers.index('Category')
    amount_idx = headers.index('Amount')

    for row in csv_lines:
        date = row[date_idx]
        amount = float(row[amount_idx]) if row[amount_idx] else 0
        desc = row[desc_idx]

        if amount == 0:
            continue

        category = detect_category(desc)

        if category is None:
            match row[category_idx]:
                case "Eating out":
                    category = "Dining Out"
                case "Entertainment":
                    category = "Days Out"
                case "Groceries":
                    category = "Groceries"
                case "Holidays":
                    category = "Holiday"
                case "Transfers":
                    category = "Transfer"
                case "Transport":
                    category = "Parking" if "park" in desc.lower() else "Transportation"

        transactions.append(create_transaction(date, -amount, desc, category))

    return transactions


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
    file = f"output/{bank}_export.csv"

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
    parser.add_argument("-b", "--bank", choices=["Lloyds", "Monzo", "Bills", "Decorating"])
    parser.add_argument("-q", "--quiet", action="store_true")

    args = parser.parse_args()

    csv_lines = parse_csv(args.file)

    match args.bank:
        case "Lloyds":
            transactions = process_lloyds(csv_lines)
        case "Natwest 7051" | "Natwest" | "Bills" | "Decorating":
            transactions = process_natwest(csv_lines)
        case "Monzo":
            transactions = process_monzo(csv_lines)
        case _:
            print(f"Unable to locate Bank: {args.bank}")
            sys.exit(1)

    if not transactions or len(transactions) == 0:
        print(f"No transactions generated for file: {args.file}")
        sys.exit(0)

    transactions = clean_up_transactions(transactions)

    export_to_csv(args.bank, transactions)


if __name__ == '__main__':
    main()
