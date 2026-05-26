# Example 3 — Unoptimized code: performance anti-patterns
import time


def build_names_list(raw_data):
    """Should use a list comprehension instead of loop + append."""
    names = []
    for item in raw_data:
        if item.get("active"):
            names.append(item["name"].strip().lower())
    return names


def build_report(items):
    """String concatenation in a loop — O(n²) memory allocation."""
    report = ""
    for item in items:
        report += f"- {item['name']}: {item['value']}\n"
        report += f"  Category: {item.get('category', 'N/A')}\n"
    return report


def filter_valid(records):
    """Uses len(x) > 0 where truthiness check suffices."""
    valid = []
    for rec in records:
        if len(rec) > 0:
            if len(rec.get("tags", [])) > 0:
                if len(rec.get("name", "")) > 0:
                    valid.append(rec)
    return valid


def compute_totals(dataset):
    """Repeated attribute lookup inside a hot loop."""
    totals = []
    config = {"multiplier": 1.5, "offset": 3.7, "rounding": 2}
    for item in dataset:
        value = item["value"]
        result = round(value * config["multiplier"] + config["offset"], config["rounding"])
        totals.append(result)
    return totals


def find_duplicates(items):
    """O(n²) duplicate detection — should use a set."""
    duplicates = []
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            if items[i] == items[j]:
                if items[i] not in duplicates:
                    duplicates.append(items[i])
    return duplicates


def flatten_matrix(matrix):
    """Nested loops with append — can be a flat list comprehension."""
    flat = []
    for row in matrix:
        for cell in row:
            flat.append(cell)
    return flat


def sum_even_squares(numbers):
    """Multiple passes where a single comprehension would do."""
    evens = []
    for n in numbers:
        if n % 2 == 0:
            evens.append(n)
    squares = []
    for n in evens:
        squares.append(n ** 2)
    total = 0
    for s in squares:
        total += s
    return total
