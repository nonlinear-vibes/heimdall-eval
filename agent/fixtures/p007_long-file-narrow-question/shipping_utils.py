"""Utility functions for the order fulfillment service."""
 
 
def celsius_to_fahrenheit(celsius):
    return (celsius * 9 / 5) + 32
 
 
def fahrenheit_to_celsius(fahrenheit):
    return (fahrenheit - 32) * 5 / 9
 
 
def format_currency(amount, currency="USD"):
    symbols = {"USD": "$", "EUR": "€", "GBP": "£"}
    symbol = symbols.get(currency, "")
    return f"{symbol}{amount:.2f}"
 
 
def slugify(text):
    return text.strip().lower().replace(" ", "-")
 
 
def is_valid_zip(zip_code):
    return zip_code.isdigit() and len(zip_code) in (5, 9)
 
 
def chunk_list(items, size):
    return [items[i:i + size] for i in range(0, len(items), size)]
 
 
def normalize_phone_number(phone):
    digits = "".join(c for c in phone if c.isdigit())
    if len(digits) == 10:
        return f"({digits[0:3]}) {digits[3:6]}-{digits[6:10]}"
    return digits
 
 
def calculate_tax(subtotal, tax_rate=0.0725):
    return round(subtotal * tax_rate, 2)
 
 
def mask_credit_card(number):
    digits = "".join(c for c in number if c.isdigit())
    if len(digits) < 4:
        return "*" * len(digits)
    return "*" * (len(digits) - 4) + digits[-4:]
 
 
def days_between(date1, date2):
    return abs((date2 - date1).days)
 
 
def is_business_day(date):
    return date.weekday() < 5
 
 
def generate_order_id(prefix="ORD"):
    import random
    return f"{prefix}-{random.randint(100000, 999999)}"
 
 
def parse_address(address_string):
    parts = [p.strip() for p in address_string.split(",")]
    return {
        "street": parts[0] if len(parts) > 0 else "",
        "city": parts[1] if len(parts) > 1 else "",
        "state_zip": parts[2] if len(parts) > 2 else "",
    }
 
 
def validate_email(email):
    return "@" in email and "." in email.split("@")[-1]
 
 
def truncate_string(text, max_length=50):
    if len(text) <= max_length:
        return text
    return text[: max_length - 3] + "..."
 
 
def merge_dicts(*dicts):
    result = {}
    for d in dicts:
        result.update(d)
    return result
 
 
def flatten_list(nested):
    result = []
    for item in nested:
        if isinstance(item, list):
            result.extend(flatten_list(item))
        else:
            result.append(item)
    return result
 
 
def calculate_discount(price, discount_percent):
    return round(price * (1 - discount_percent / 100), 2)
 
 
def is_weekend(date):
    return date.weekday() >= 5
 
 
def word_count(text):
    return len(text.split())
 
 
def reverse_words(text):
    return " ".join(reversed(text.split()))
 
 
def dedupe_list(items):
    seen = set()
    result = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result
 
 
def calculate_bmi(weight_kg, height_m):
    return round(weight_kg / (height_m ** 2), 1)
 
 
def clamp(value, min_value, max_value):
    return max(min_value, min(value, max_value))
 
 
def calculate_shipping_cost(weight_kg, distance_km, is_express=False, is_fragile=False):
    """
    Calculates the shipping cost for a package.
 
    Parameters considered:
    - weight_kg: base rate is $2.50 per kg
    - distance_km: adds $0.05 per km beyond the first 50 km (first 50 km free)
    - is_express: if True, applies a 1.75x multiplier to the subtotal
    - is_fragile: if True, adds a flat $4.00 handling fee (applied after
      the express multiplier, not before)
 
    Returns the final cost rounded to 2 decimal places. Raises ValueError
    if weight_kg or distance_km is negative.
    """
    if weight_kg < 0 or distance_km < 0:
        raise ValueError("weight_kg and distance_km must be non-negative")
 
    base_rate = 2.50
    subtotal = weight_kg * base_rate
 
    billable_distance = max(0, distance_km - 50)
    subtotal += billable_distance * 0.05
 
    if is_express:
        subtotal *= 1.75
 
    if is_fragile:
        subtotal += 4.00
 
    return round(subtotal, 2)
 
 
def format_tracking_number(carrier, number):
    return f"{carrier.upper()}-{number}"
