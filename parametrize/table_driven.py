"""Table-driven tests using pytest.mark.parametrize.

Parametrize runs the same test function with different inputs,
keeping tests DRY and easy to add new cases.
"""
import pytest
from typing import Any


# ─────────────────────────── Functions Under Test ──────────────────────

def is_palindrome(s: str) -> bool:
    cleaned = "".join(c.lower() for c in s if c.isalnum())
    return cleaned == cleaned[::-1]


def fizzbuzz(n: int) -> str:
    if n % 15 == 0:
        return "FizzBuzz"
    elif n % 3 == 0:
        return "Fizz"
    elif n % 5 == 0:
        return "Buzz"
    return str(n)


def roman_to_int(s: str) -> int:
    vals = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
    result = 0
    prev = 0
    for ch in reversed(s):
        val = vals[ch]
        result += val if val >= prev else -val
        prev = val
    return result


def calculate_discount(price: float, pct: float) -> float:
    if pct < 0 or pct > 100:
        raise ValueError(f"Discount must be 0-100, got {pct}")
    return round(price * (1 - pct / 100), 2)


# ─────────────────────────── Parametrized Tests ─────────────────────────

@pytest.mark.parametrize("input_str,expected", [
    ("racecar", True),
    ("hello", False),
    ("A man a plan a canal Panama", True),
    ("Was it a car or a cat I saw", True),
    ("", True),  # empty string is palindrome
    ("a", True),  # single char
    ("No lemon no melon", True),
    ("python", False),
])
def test_palindrome(input_str: str, expected: bool):
    assert is_palindrome(input_str) == expected


@pytest.mark.parametrize("n,expected", [
    (1, "1"),
    (3, "Fizz"),
    (5, "Buzz"),
    (15, "FizzBuzz"),
    (30, "FizzBuzz"),
    (9, "Fizz"),
    (10, "Buzz"),
    (7, "7"),
    (100, "Buzz"),
])
def test_fizzbuzz(n: int, expected: str):
    assert fizzbuzz(n) == expected


@pytest.mark.parametrize("roman,expected_int", [
    ("I", 1),
    ("IV", 4),
    ("IX", 9),
    ("XIV", 14),
    ("XLII", 42),
    ("XCIX", 99),
    ("CDXLIV", 444),
    ("MCMXCIX", 1999),
    ("MMXXIV", 2024),
])
def test_roman_to_int(roman: str, expected_int: int):
    assert roman_to_int(roman) == expected_int


@pytest.mark.parametrize("price,pct,expected", [
    (100.00, 0, 100.00),
    (100.00, 10, 90.00),
    (100.00, 25, 75.00),
    (100.00, 100, 0.00),
    (99.99, 10, 89.99),
    (49.99, 20, 39.99),
])
def test_calculate_discount(price: float, pct: float, expected: float):
    assert calculate_discount(price, pct) == expected


@pytest.mark.parametrize("price,pct", [
    (100, -1),
    (100, 101),
    (100, -0.001),
])
def test_calculate_discount_invalid(price: float, pct: float):
    with pytest.raises(ValueError, match="Discount must be 0-100"):
        calculate_discount(price, pct)


# ─────────────────────────── Indirect Parametrize ──────────────────────

@pytest.fixture
def user_with_role(request):
    """Fixture that accepts parameter from indirect parametrize."""
    role = request.param
    return {"id": 1, "name": "Alice", "role": role, "is_active": True}


@pytest.mark.parametrize("user_with_role,can_access_admin", [
    ("admin", True),
    ("user", False),
    ("moderator", False),
], indirect=["user_with_role"])
def test_admin_access(user_with_role, can_access_admin):
    """Test admin access by role using indirect parametrize."""
    has_access = user_with_role["role"] == "admin"
    assert has_access == can_access_admin


# ─────────────────────────── Multiple Parameter Sets ───────────────────

@pytest.mark.parametrize("input_val,type_check,expected_str", [
    (42, int, "42"),
    (3.14, float, "3.14"),
    ("hello", str, "hello"),
    (True, bool, "True"),
    (None, type(None), "None"),
])
def test_string_conversion(input_val: Any, type_check: type, expected_str: str):
    """Test string conversion for various types."""
    assert isinstance(input_val, type_check)
    assert str(input_val) == expected_str


# ─────────────────────────── Combining parametrize ─────────────────────

@pytest.mark.parametrize("a", [1, 2, 3])
@pytest.mark.parametrize("b", [10, 20])
def test_multiplication_table(a: int, b: int):
    """Creates 6 test cases: 1*10, 2*10, 3*10, 1*20, 2*20, 3*20."""
    result = a * b
    assert result == a * b  # trivial, but shows the pattern
    assert isinstance(result, int)
