import csv
import os

LEDGER_FILE = "2026_cra_ledger.csv"

def analyze_payouts_and_allocations(ledger_path=LEDGER_FILE):
    """
    Audits settled payouts from 2026_cra_ledger.csv, summarizes CRA T2125 tax totals,
    and calculates the exact 50/30/20 profit-allocation split.
    """
    print("\n==================================================")
    print("     WONDERFUL GEMS POINT - PAYOUT & TAX AUDIT    ")
    print("==================================================\n")

    if not os.path.exists(ledger_path):
        print(f"Error: Ledger file '{ledger_path}' not found at project root.")
        print("Please create 2026_cra_ledger.csv before running this audit.\n")
        return

    gross_revenue = 0.0
    operating_expenses = 0.0
    revenue_count = 0
    expense_count = 0

    with open(ledger_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                # Support both Amount_CAD and legacy Amount_USD headers
                amount_str = row.get("Amount_CAD") or row.get("Amount_USD") or "0"
                amount = float(amount_str)
                category = row.get("Category", "").strip().upper()

                if category == "REVENUE":
                    gross_revenue += amount
                    revenue_count += 1
                elif category == "EXPENSE":
                    operating_expenses += amount
                    expense_count += 1
            except (ValueError, KeyError):
                continue

    net_cleared = gross_revenue - operating_expenses

    print(f"Total Revenue Entries (Line 8230):   {revenue_count} transactions")
    print(f"Total Expense Entries (Line 8810):   {expense_count} transactions")
    print("--------------------------------------------------")
    print(f"Gross Business Revenue (Line 8230):  ${gross_revenue:10.2f} CAD")
    print(f"Total Operating Expenses (Line 8810):${operating_expenses:10.2f} CAD")
    print("--------------------------------------------------")
    print(f"Current Net Cleared Balance:          ${net_cleared:10.2f} CAD\n")

    if net_cleared > 0:
        fulfillment_reserve = net_cleared * 0.50
        operating_overhead  = net_cleared * 0.30
        owner_draw          = net_cleared * 0.20

        print("==================================================")
        print("        50/30/20 PROFIT ALLOCATION SPLIT          ")
        print("==================================================")
        print(f"1. Fulfillment Reserve (50%):          ${fulfillment_reserve:10.2f} CAD")
        print(f"   -> Retain in CIBC for Sellvia product COGS & shipping")
        print(f"2. Operating Overhead  (30%):          ${operating_overhead:10.2f} CAD")
        print(f"   -> Hold for Shopify app billing & software subscriptions")
        print(f"3. Owner Draw Transfer (20%):          ${owner_draw:10.2f} CAD")
        print(f"   -> Transferrable net profit draw")
        print("==================================================\n")
    else:
        print("Notice: Current net balance is zero or negative. No profit allocation available.\n")

if __name__ == "__main__":
    analyze_payouts_and_allocations()
