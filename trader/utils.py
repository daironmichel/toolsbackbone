def get_limit_price(current_price):
    price = current_price
    digits = 0
    if price > 0:
        while price > 0:
            digits += 1
            price //= 10

    else:
        while price < 0:
            digits += 1
            price *= 10
