from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional

@dataclass
class CatalogItem:
    id: str
    name: str
    price: float
    category: str
    description: str

class CatalogManager:
    def __init__(self):
        self.items: Dict[str, CatalogItem] = {
            "burger_1": CatalogItem("burger_1", "Zinger Burger", 5.99, "food", "Crispy spiced chicken fillet burger"),
            "burger_2": CatalogItem("burger_2", "Classic Beef Burger", 6.99, "food", "Grilled beef patty with cheese"),
            "fries_1": CatalogItem("fries_1", "Regular Fries", 2.49, "sides", "Crispy golden french fries"),
            "drink_1": CatalogItem("drink_1", "Soft Drink", 1.99, "drinks", "Chilled soda can"),
        }

    def search_menu(self, query: str) -> List[CatalogItem]:
        q = query.lower()
        return [i for i in self.items.values() if q in i.name.lower() or q in i.description.lower() or q in i.category.lower()]

    def get_full_menu_text(self) -> str:
        lines = ["--- MENU ---"]
        for i in self.items.values():
            lines.append(f"? {i.name} - ${i.price:.2f} ({i.description})")
        return "\n".join(lines)
