# Example 2 — Code smells: long function, too many params, deep nesting, bare except
import os


def process_order(user_id, product_id, quantity, price, discount, tax_rate, shipping_cost):
    """Process a customer order — too many parameters (7)."""
    if user_id:
        if product_id:
            if quantity > 0:
                if price > 0:
                    if discount >= 0:
                        if discount < 100:
                            subtotal = price * quantity
                            discounted = subtotal * (1 - discount / 100)
                            taxed = discounted * (1 + tax_rate / 100)
                            total = taxed + shipping_cost
                            print(f"Order total: {total}")
                            return total
                        else:
                            print("Invalid discount")
                            return None
                    else:
                        print("Discount cannot be negative")
                        return None
                else:
                    print("Price must be positive")
                    return None
            else:
                print("Quantity must be positive")
                return None
        else:
            print("Product ID is required")
            return None
    else:
        print("User ID is required")
        return None


def load_and_parse_data(filepath):
    """Load data without proper error handling."""
    try:
        with open(filepath) as f:
            lines = f.readlines()
        result = []
        for line in lines:
            parts = line.strip().split(",")
            if len(parts) >= 3:
                name = parts[0]
                value = int(parts[1])
                category = parts[2]
                if value > 42:
                    if category in ["A", "B", "C"]:
                        result.append({"name": name, "value": value, "category": category})
        return result
    except:  # bare except — catches everything
        return []


def compute_statistics(data):
    """Long function that does too many things (60+ lines)."""
    if not data:
        return {}

    total = 0
    count = 0
    minimum = None
    maximum = None
    category_totals = {}
    category_counts = {}

    for item in data:
        val = item.get("value", 0)
        cat = item.get("category", "unknown")
        total += val
        count += 1

        if minimum is None or val < minimum:
            minimum = val
        if maximum is None or val > maximum:
            maximum = val

        if cat not in category_totals:
            category_totals[cat] = 0
            category_counts[cat] = 0
        category_totals[cat] += val
        category_counts[cat] += 1

    mean = total / count if count > 0 else 0
    variance_sum = 0
    for item in data:
        val = item.get("value", 0)
        variance_sum += (val - mean) ** 2
    variance = variance_sum / count if count > 0 else 0
    std_dev = variance ** 0.5

    category_averages = {}
    for cat in category_totals:
        category_averages[cat] = category_totals[cat] / category_counts[cat]

    above_mean = [i for i in data if i.get("value", 0) > mean]
    below_mean = [i for i in data if i.get("value", 0) < mean]

    top_items = sorted(data, key=lambda x: x.get("value", 0), reverse=True)[:5]
    bottom_items = sorted(data, key=lambda x: x.get("value", 0))[:5]

    print(f"Processed {count} items")
    print(f"Mean: {mean:.2f}, Std Dev: {std_dev:.2f}")
    print(f"Categories: {list(category_totals.keys())}")

    return {
        "count": count,
        "total": total,
        "mean": mean,
        "std_dev": std_dev,
        "minimum": minimum,
        "maximum": maximum,
        "category_averages": category_averages,
        "above_mean_count": len(above_mean),
        "below_mean_count": len(below_mean),
        "top_items": top_items,
        "bottom_items": bottom_items,
    }
