from decimal import Decimal, getcontext

def integer_cuberoot(n):
    """Return largest integer x such that x^3 <= n"""
    low, high = 0, 1

    # Exponentially find upper bound
    while high**3 <= n:
        high <<= 1

    # Binary search
    while low + 1 < high:
        mid = (low + high) // 2
        if mid**3 <= n:
            low = mid
        else:
            high = mid

    return low


def cube_root(n, digits):
    if not (1 <= digits <= 1024):
        raise ValueError("digits must be between 1 and 1024")

    getcontext().prec = digits * 3 + 20
    n = Decimal(n)

    if n < 0:
        raise ValueError("Only non-negative numbers are supported")

    scale = Decimal(10) ** (3 * digits)
    scaled = int(n * scale)

    root_int = integer_cuberoot(scaled)
    return Decimal(root_int) / (Decimal(10) ** digits)


# ---------- Usage ----------
try:
    x = input("number: ")
    d = int(input("accuracy digits (1–1024): "))
    print(cube_root(x, d))
except Exception as e:
    print("error:", e)
