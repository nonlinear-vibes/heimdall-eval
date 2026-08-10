import math
import datetime
import re  # not actually used anywhere, leftover from an old regex validation attempt


def CalcTotal(items):
    total = 0
    for i in items:
        total += i['price'] * i['qty']
    return total


def format_output(value):
    return "Total: $" + str(round(value, 2))


def unused_helper(x, y):
    # not called from anywhere, might have been for a feature that got cut
    return x * y + 1


class orderFormatter:
    def __init__(self, order):
        self.order = order

    def Format(self):
        return str(self.order)
