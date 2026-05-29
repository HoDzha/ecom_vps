from __future__ import annotations

POLICY_BOOK = [
    {
        "id": "return-standard",
        "title": "Standard Return Policy",
        "text": "Returns are allowed within 30 days if item is unused.",
        "tags": ["return", "refund"],
    },
    {
        "id": "late-delivery-refund",
        "title": "Late Delivery Refund",
        "text": "If delivery is delayed by more than 5 days, shipping fee is refundable.",
        "tags": ["late", "delivery", "refund"],
    },
    {
        "id": "payment-failure-retry",
        "title": "Payment Failure Handling",
        "text": "For soft declines, retry once and request updated card details.",
        "tags": ["payment", "failure", "card"],
    },
]

CUSTOMER_RECORDS = {
    "cust_001": {
        "customer_id": "cust_001",
        "tier": "gold",
        "returns_last_30d": 1,
        "fraud_risk": "low",
    },
    "cust_002": {
        "customer_id": "cust_002",
        "tier": "standard",
        "returns_last_30d": 5,
        "fraud_risk": "medium",
    },
    "cust_003": {
        "customer_id": "cust_003",
        "tier": "new",
        "returns_last_30d": 0,
        "fraud_risk": "high",
    },
}

WAREHOUSE = {
    "ord_1001": {
        "order_id": "ord_1001",
        "status": "delivered",
        "delay_days": 7,
        "item_condition": "sealed",
    },
    "ord_1002": {
        "order_id": "ord_1002",
        "status": "in_transit",
        "delay_days": 2,
        "item_condition": "unknown",
    },
    "ord_1003": {
        "order_id": "ord_1003",
        "status": "delivered",
        "delay_days": 0,
        "item_condition": "opened",
    },
}
