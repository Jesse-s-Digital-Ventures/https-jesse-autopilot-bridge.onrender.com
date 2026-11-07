import csv
import os

def generate_tax_summary(ledger_file="2026_cra_ledger.csv"):
    if not os.path.exists(ledger_file):
        print(f"Error: Ledger file '{ledger_file}' not found. Run tax_logger.py first to create entries.")
        return

    gross_revenue = 0.0
    expenses_by_line = {}

    with open(ledger_file, mode="r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                amount = float(row["Amount_CAD"])
                category = row["Category"].upper()
                cra_line = row["CRA_Line"]

                if category == "REVENUE":
                    gross_revenue += amount
                elif category == "EXPENSE":
                    expenses_by_line[cra_line] = expenses_by_line.get(cra_line, 0.0) + amount
            except (ValueError, KeyError) as e:
                print(f"Skipping malformed row: {row} ({e})")

    total_expenses = sum(expenses_by_line.values())
    net_income = gross_revenue - total_expenses

    print("\n==========================================")
    print("      CRA T2125 STATEMENT SUMMARY        ")
    print("==========================================")
    print(f"Line 8230 (Gross Business Revenue): ${gross_revenue:.2f} CAD")
    print("------------------------------------------")
    print("Expenses Breakdown:")
    if expenses_by_line:
        for line, total in sorted(expenses_by_line.items()):
            print(f"  - {line}: ${total:.2f} CAD")
    else:
        print("  - No expenses recorded yet.")
    print("------------------------------------------")
    print(f"Total Expenses:                     ${total_expenses:.2f} CAD")
    print("==========================================")
    print(f"NET TAXABLE BUSINESS INCOME:        ${net_income:.2f} CAD")
    print("==========================================\n")

if __name__ == "__main__":
    generate_tax_summary()
