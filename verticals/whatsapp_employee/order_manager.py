from __future__ import annotations
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

@dataclass
class Order:
    id: str
    customer_phone: str
    items: List[Dict[str, Any]]
    total_amount: float
    delivery_address: str
    status: str = "pending"  # pending, confirmed, kitchen, delivered
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

class OrderManager:
    def __init__(self):
        self.orders: Dict[str, Order] = {}

    def create_order(self, customer_phone: str, items: List[Dict[str, Any]], total: float, address: str) -> Order:
        order_id = f"ord_{uuid.uuid4().hex[:6]}"
        order = Order(
            id=order_id,
            customer_phone=customer_phone,
            items=items,
            total_amount=total,
            delivery_address=address,
            status="confirmed",
        )
        self.orders[order_id] = order
        return order
