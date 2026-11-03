import os
import json
from decimal import Decimal, ROUND_HALF_UP

# 1. Load rules dynamically from config/cashflow_config.json
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "..", "config", "cashflow_config.json")

def load_config():
    """Loads the cashflow configuration JSON file."""
    if not os.path.exists(CONFIG_PATH):
        raise FileNotFoundError(f"Configuration file not found at {CONFIG_PATH}")
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)

# Load configuration values
config = load_config()
alloc_pcts = config.get("allocation", {})

# Convert percentages to Decimal for high-precision currency math
SPLIT = {
    "fulfillment_reserve": Decimal(str(alloc_pcts.get("fulfillment_reserve_pct", 0.50))),
    "ad_reinvestment":     Decimal(str(alloc_pcts.get("ad_reinvestment_pct", 0.30))),
    "owner_draw":          Decimal(str(alloc_pcts.get("owner_draw_pct", 0.20)))
}


def allocate_payout(amount: float) -> dict:
    """
    Splits an incoming payout into exact currency allocations down to the penny.
    Pushes any remainder rounding pennies into the fulfillment reserve.
    """
    amt = Decimal(str(amount)).quantize(Decimal("0.01"))
    if amt <= 0:
        raise ValueError("Payout amount must be positive")
        
    out = {
        k: (amt * p).quantize(Decimal("0.01"), ROUND_HALF_UP)
        for k, p in SPLIT.items()
    }
    
    # Push rounding remainder into fulfillment reserve so the total sum is 100% exact
    remainder = amt - sum(out.values())
    out["fulfillment_reserve"] += remainder
    
    # Return floats for easy database insertion or API response
    return {k: float(v) for k, v in out.items()}


if __name__ == "__main__":
    # Test allocation with expected payout number ($101.44)
    sample_amount = 101.44
    result = allocate_payout(sample_amount)
    
    print("=" * 45)
    print(f"💰 DYNAMIC PAYOUT ALLOCATION ({config['store']['platform']})")
    print(f"Total Gross Settlement: ${sample_amount:,.2f} {config['store']['currency']}")
    print("=" * 45)
    print(f"📦 Fulfillment Reserve ({SPLIT['fulfillment_reserve']*100:.0f}%):  ${result['fulfillment_reserve']:,.2f}")
    print(f"📣 Ad Reinvestment     ({SPLIT['ad_reinvestment']*100:.0f}%):  ${result['ad_reinvestment']:,.2f}")
    print(f"💵 Owner Draw          ({SPLIT['owner_draw']*100:.0f}%):  ${result['owner_draw']:,.2f}")
    print("=" * 45)
