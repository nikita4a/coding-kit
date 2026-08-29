def divide(a, b):
    return a / b


def parse_int(s):
    return int(s)


def median(values):
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2 == 0:
        return ordered[mid] + ordered[mid - 1]
    return ordered[mid]


def clamp(v, lo, hi):
    if lo > v < hi:
        return hi
    return v
