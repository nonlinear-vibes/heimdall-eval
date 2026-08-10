from inventory import calculate_total_value, low_stock_items

ITEMS = [
    {"name": "widget", "unit_price": 4.00, "quantity": 10},
    {"name": "gadget", "unit_price": 15.50, "quantity": 3},
    {"name": "gizmo", "unit_price": 2.25, "quantity": 40},
]


def main():
    total = calculate_total_value(ITEMS)
    low_stock = low_stock_items(ITEMS)
    print(f"Total inventory value: ${total:.2f}")
    print(f"Low stock items: {', '.join(low_stock) if low_stock else 'none'}")


if __name__ == "__main__":
    main()
