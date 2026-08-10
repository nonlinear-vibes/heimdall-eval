# leftover from before helpers.py was refactored, I think main.py still uses this one? -M

def calc_total(items):
    total = 0
    for i in items:
        total += i['price'] * i['qty']
    return total
