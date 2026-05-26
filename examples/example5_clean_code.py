"""Inventory management module — demonstrates clean Python code practices."""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)

LOW_STOCK_THRESHOLD = 10
MAX_REORDER_QUANTITY = 1000


class Category(Enum):
    """Product category classifications."""

    ELECTRONICS = "electronics"
    CLOTHING = "clothing"
    FOOD = "food"
    OTHER = "other"


@dataclass
class Product:
    """Represents a product in the inventory."""

    sku: str
    name: str
    price: float
    quantity: int
    category: Category
    tags: list[str] = field(default_factory=list)

    def is_available(self) -> bool:
        """Return True if the product has stock."""
        return self.quantity > 0

    def is_low_stock(self) -> bool:
        """Return True if quantity is below the low-stock threshold."""
        return 0 < self.quantity < LOW_STOCK_THRESHOLD

    def apply_discount(self, percent: float) -> float:
        """Return the discounted price for a given percentage (0-100)."""
        if not 0 <= percent <= 100:
            raise ValueError(f"Discount percent must be between 0 and 100, got {percent}")
        return round(self.price * (1 - percent / 100), 2)


class Inventory:
    """Manages a collection of products with search and reporting capabilities."""

    def __init__(self) -> None:
        self._products: dict[str, Product] = {}

    def add_product(self, product: Product) -> None:
        """Add or replace a product by SKU."""
        self._products[product.sku] = product
        logger.info("Added product: %s (%s)", product.name, product.sku)

    def get_product(self, sku: str) -> Optional[Product]:
        """Return the product for the given SKU, or None if not found."""
        return self._products.get(sku)

    def remove_product(self, sku: str) -> bool:
        """Remove a product by SKU. Return True if removed, False if not found."""
        if sku not in self._products:
            return False
        del self._products[sku]
        logger.info("Removed product: %s", sku)
        return True

    def search_by_category(self, category: Category) -> list[Product]:
        """Return all products in the given category."""
        return [p for p in self._products.values() if p.category == category]

    def search_by_tag(self, tag: str) -> list[Product]:
        """Return all products that have the given tag."""
        return [p for p in self._products.values() if tag in p.tags]

    def get_low_stock_products(self) -> list[Product]:
        """Return products that are below the low-stock threshold."""
        return [p for p in self._products.values() if p.is_low_stock()]

    def get_out_of_stock_products(self) -> list[Product]:
        """Return products with zero quantity."""
        return [p for p in self._products.values() if not p.is_available()]

    def restock(self, sku: str, quantity: int) -> None:
        """Add quantity to an existing product's stock."""
        if quantity <= 0:
            raise ValueError(f"Restock quantity must be positive, got {quantity}")
        if quantity > MAX_REORDER_QUANTITY:
            raise ValueError(f"Restock quantity cannot exceed {MAX_REORDER_QUANTITY}")

        product = self._products.get(sku)
        if product is None:
            raise KeyError(f"Product with SKU '{sku}' not found")

        product.quantity += quantity
        logger.info("Restocked %s: +%d units (total: %d)", sku, quantity, product.quantity)

    def generate_report(self) -> dict:
        """Return a summary report of the current inventory state."""
        products = list(self._products.values())
        total_value = sum(p.price * p.quantity for p in products)
        by_category = {
            cat.value: len([p for p in products if p.category == cat])
            for cat in Category
        }
        return {
            "total_products": len(products),
            "total_value": round(total_value, 2),
            "available": len([p for p in products if p.is_available()]),
            "low_stock": len(self.get_low_stock_products()),
            "out_of_stock": len(self.get_out_of_stock_products()),
            "by_category": by_category,
        }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    inventory = Inventory()
    inventory.add_product(Product("SKU-001", "Laptop", 999.99, 15, Category.ELECTRONICS, ["tech", "portable"]))
    inventory.add_product(Product("SKU-002", "T-Shirt", 29.99, 8, Category.CLOTHING, ["casual"]))
    inventory.add_product(Product("SKU-003", "Coffee Beans", 14.99, 0, Category.FOOD, ["beverage"]))

    report = inventory.generate_report()
    print(f"Inventory report: {report}")

    low_stock = inventory.get_low_stock_products()
    print(f"Low stock items: {[p.name for p in low_stock]}")
