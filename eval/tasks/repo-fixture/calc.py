def divide(a, b):
    return a / b


def parse_int(s):
    return int(s)


def clamp(v, lo, hi):
    if lo > v < hi:
        return hi
    return v
