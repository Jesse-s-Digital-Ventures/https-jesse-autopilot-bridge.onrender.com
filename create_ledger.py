import os
import csv

# Path to the ledger file
LEDGER_FILE = "2026_cra_ledger.csv"

# CRA-compliant header schema
HEADERS = ["Date", "Category", "Description", "Amount_CAD", "Vendor", "CRA_Line"]

# Master transaction list (29 rows through Nov 11, 2026)
TRANSACTIONS = [
    {"Date": "2026-11-01 10:15:00", "Category": "REVENUE", "Description": "Sellvia Customer Order Revenue", "Amount_CAD": 455.05, "Vendor": "Shopify", "CRA_Line": "Line 8230"},
    {"Date": "2026-11-06 17:32:00", "Category": "EXPENSE", "Description": "Sellvia Wholesale Order Fulfillment", "Amount_CAD": 30.45, "Vendor": "Sellvia", "CRA_Line": "Line 8810"},
    {"Date": "2026-11-06 23:07:00", "Category": "EXPENSE", "Description": "Sellvia Wholesale Order Fulfillment", "Amount_CAD": 19.28, "Vendor": "Sellvia", "CRA_Line": "Line 8810"},
    {"Date": "2026-11-07 03:45:00", "Category": "REVENUE", "Description": "Order Nov 7 Store Sale", "Amount_CAD": 19.99, "Vendor": "Sellvia Ads", "CRA_Line": "Line 8230"},
    {"Date": "2026-11-07 05:30:46", "Category": "REVENUE", "Description": "Order WON-WTTW2E1XQ380", "Amount_CAD": 20.99, "Vendor": "Sellvia Ads", "CRA_Line": "Line 8230"},
    {"Date": "2026-11-07 06:00:37", "Category": "REVENUE", "Description": "Order WON-0CB7057E4Z62", "Amount_CAD": 20.99, "Vendor": "Sellvia Ads", "CRA_Line": "Line 8230"},
    {"Date": "2026-11-07 12:10:00", "Category": "EXPENSE", "Description": "Shopify Bill #A610817303 (POS Pro & Apps)", "Amount_CAD": 133.09, "Vendor": "Shopify", "CRA_Line": "Line 8810"},
    {"Date": "2026-11-07 15:30:15", "Category": "REVENUE", "Description": "Order WON-Q1L7VJN7T820", "Amount_CAD": 12.99, "Vendor": "Sellvia Ads", "CRA_Line": "Line 8230"},
    {"Date": "2026-11-08 03:46:00", "Category": "REVENUE", "Description": "Order Nov 8 Store Sale", "Amount_CAD": 11.99, "Vendor": "Sellvia Ads", "CRA_Line": "Line 8230"},
    {"Date": "2026-11-08 04:45:00", "Category": "REVENUE", "Description": "Order Nov 8 Store Sale", "Amount_CAD": 9.99, "Vendor": "Sellvia Ads", "CRA_Line": "Line 8230"},
    {"Date": "2026-11-08 04:45:43", "Category": "REVENUE", "Description": "Order WON-12B1ZKYFEWFB", "Amount_CAD": 11.99, "Vendor": "Sellvia Ads", "CRA_Line": "Line 8230"},
    {"Date": "2026-11-08 04:45:43", "Category": "REVENUE", "Description": "Order Nov 8 Store Sale", "Amount_CAD": 12.99, "Vendor": "Sellvia Ads", "CRA_Line": "Line 8230"},
    {"Date": "2026-11-09 08:00:36", "Category": "REVENUE", "Description": "Order WON-S9NNJA84X779", "Amount_CAD": 9.99, "Vendor": "Sellvia Ads", "CRA_Line": "Line 8230"},
    {"Date": "2026-11-09 07:00:00", "Category": "REVENUE", "Description": "Order #1048 Store Sale", "Amount_CAD": 19.99, "Vendor": "Sellvia Ads", "CRA_Line": "Line 8230"},
    {"Date": "2026-11-09 04:30:00", "Category": "REVENUE", "Description": "Order #1049 Store Sale", "Amount_CAD": 12.99, "Vendor": "Sellvia Ads", "CRA_Line": "Line 8230"},
    {"Date": "2026-11-09 10:00:22", "Category": "REVENUE", "Description": "Order WON-XKCJKSE3LZ8C", "Amount_CAD": 8.99, "Vendor": "Sellvia Ads", "CRA_Line": "Line 8230"},
    {"Date": "2026-11-09 16:30:17", "Category": "REVENUE", "Description": "Order WON-OFHX2FTPIVB7", "Amount_CAD": 8.99, "Vendor": "Sellvia Ads", "CRA_Line": "Line 8230"},
    {"Date": "2026-11-09 23:15:00", "Category": "REVENUE", "Description": "Order Nov 9 11:15 PM Sale", "Amount_CAD": 8.99, "Vendor": "Sellvia Ads", "CRA_Line": "Line 8230"},
    {"Date": "2026-11-10 01:15:29", "Category": "REVENUE", "Description": "Order WON-R48BGLMDQ452", "Amount_CAD": 8.99, "Vendor": "Sellvia Ads", "CRA_Line": "Line 8230"},
    {"Date": "2026-11-10 06:16:00", "Category": "REVENUE", "Description": "Order Nov 10 6:16 AM Sale", "Amount_CAD": 8.99, "Vendor": "Sellvia Ads", "CRA_Line": "Line 8230"},
    {"Date": "2026-11-10 08:15:00", "Category": "REVENUE", "Description": "Order Nov 10 8:15 AM Sale", "Amount_CAD": 10.99, "Vendor": "Sellvia Ads", "CRA_Line": "Line 8230"},
    {"Date": "2026-11-10 10:15:25", "Category": "REVENUE", "Description": "Order WON-YTJO7SWDWUVQ", "Amount_CAD": 7.99, "Vendor": "Sellvia Ads", "CRA_Line": "Line 8230"},
    {"Date": "2026-11-11 01:15:42", "Category": "REVENUE", "Description": "Order WON-PWH6CWMNSZ35", "Amount_CAD": 9.99, "Vendor": "Sellvia Ads", "CRA_Line": "Line 8230"},
    {"Date": "2026-11-11 02:00:00", "Category": "EXPENSE", "Description": "Sellvia Store Addon Purchase", "Amount_CAD": 378.00, "Vendor": "Sellvia", "CRA_Line": "Line 8810"},
    {"Date": "2026-11-11 02:30:00", "Category": "EXPENSE", "Description": "Sellvia Wholesale Order Fulfillment (WON-PWH6CWMNSZ35)", "Amount_CAD": 4.95, "Vendor": "Sellvia", "CRA_Line": "Line 8810"},
    {"Date": "2026-11-11 04:17:00", "Category": "REVENUE", "Description": "Order Nov 11 4:17 AM Sale", "Amount_CAD": 19.98, "Vendor": "Sellvia Ads", "CRA_Line": "Line 8230"},
    {"Date": "2026-11-11 06:01:00", "Category": "REVENUE", "Description": "Order Nov 11 6:01 AM Sale", "Amount_CAD": 10.99, "Vendor": "Sellvia Ads", "CRA_Line": "Line 8230"},
    {"Date": "2026-11-11 07:45:29", "Category": "REVENUE", "Description": "Order WON-34B7IPOO2SMI", "Amount_CAD": 11.99, "Vendor": "Sellvia Ads", "CRA_Line": "Line 8230"}
]

def create_ledger():
    """Writes the full transaction ledger to CSV and prints current financial totals."""
    with open(LEDGER_FILE, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=HEADERS)
        writer.writeheader()
        writer.writerows(TRANSACTIONS)
    
    total_revenue = sum(t["Amount_CAD"] for t in TRANSACTIONS if t["Category"] == "REVENUE")
    total_expenses = sum(t["Amount_CAD"] for t in TRANSACTIONS if t["Category"] == "EXPENSE")
    net_profit = total_revenue - total_expenses

    print(f"✅ Generated '{LEDGER_FILE}' with {len(TRANSACTIONS)} rows.")
    print(f"💰 Gross Revenue (CRA Line 8230): ${total_revenue:.2f} CAD")
    print(f"📉 Total Expenses (CRA Line 8810): ${total_expenses:.2f} CAD")
    print(f"💵 Net Ledger Profit: ${net_profit:.2f} CAD")

if __name__ == "__main__":
    create_ledger()
