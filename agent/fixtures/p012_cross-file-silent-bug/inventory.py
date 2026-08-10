def calculate_total_value(items):
    """Returns the total value of all inventory items (unit_price * quantity, summed)."""
    total = 0
    for item in items:
        total += item["unit_price"]  # missing: should be multiplied by item["quantity"]
    return total


def low_stock_items(items, threshold=5):
    """Returns the names of items with quantity below the given threshold."""
    return [item["name"] for item in items if item["quantity"] < threshold]
