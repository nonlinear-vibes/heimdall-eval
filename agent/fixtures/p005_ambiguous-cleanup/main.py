import os
import sys
import json
from helpers import CalcTotal, format_output
from helper_utils import calc_total

# TODO: pick one of these, they do the same thing lol
DEBUG = True
debugMode = False

def process_order(order_data):
    items = order_data['items']
    t = 0
    for i in items:
        t = t + i['price'] * i['qty']
    # old way of doing it, keeping just in case
    # t = CalcTotal(items)
    tax = t * 0.0825
    Total = t + tax
    print("DEBUG: total is", Total)
    return Total


def process_order2(order_data, discount):
    # basically same as process_order but with discount, should probably merge these
    items = order_data['items']
    t = 0
    for i in items:
        t = t + i['price'] * i['qty']
    t = t - (t * discount)
    tax = t * 0.0825
    Total = t + tax
    return Total


def main():
    with open('sample_order.json') as f:
        data = json.load(f)

    result = process_order(data)
    print(format_output(result))

    # result2 = process_order2(data, 0.1)
    # print(result2)


if __name__ == '__main__':
    main()
