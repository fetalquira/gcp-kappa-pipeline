from pydantic import (
    BaseModel,
    Field,
    field_validator,
    model_validator,
    computed_field
)
from typing import Dict, List, Optional
from enum import Enum
from datetime import date, time, timedelta

# --- ENUMS (For Strict Dropdowns) ---
class OrderType(str, Enum):
    DELIVERY = "Delivery"
    PICKUP = "Pick-up"

class BakeryProduct(str, Enum):
    SOURDOUGH = "Sourdough Loaf"
    CROISSANT = "Butter Croissant"
    MANGO_CAKE = "Mango Supreme Cake"
    BROWNIES = "Fudge Brownies"
    ENSAYMADA = "Classic Ensaymada"

class EnsaymadaVariants(str, Enum):
    UBE = "Ube"
    CHEESE = "Cheese"
    CHOCOLATE = "Chocolate"

ALLOWED_VARIANTS: Dict[BakeryProduct, List[str]] = {
    BakeryProduct.SOURDOUGH: ["Standard"],
    BakeryProduct.CROISSANT: ["Standard"],
    BakeryProduct.MANGO_CAKE: ["Standard"],
    BakeryProduct.BROWNIES: ["Standard"],
    BakeryProduct.ENSAYMADA: [v.value for v in EnsaymadaVariants]
}

# The Price Map: Keyed by the Enum Value
PRODUCT_PRICES = {
    BakeryProduct.SOURDOUGH: {"Standard": 250.0},
    BakeryProduct.CROISSANT: {"Standard": 85.0},
    BakeryProduct.MANGO_CAKE: {"Standard": 1200.0},
    BakeryProduct.BROWNIES: {"Standard": 450.0},
    BakeryProduct.ENSAYMADA: {
        EnsaymadaVariants.UBE.value: 100.0,
        EnsaymadaVariants.CHEESE.value: 110.0,
        EnsaymadaVariants.CHOCOLATE.value: 105.0
    }
}

# --- NESTED MODELS ---
class OrderItem(BaseModel):
    product_name: BakeryProduct
    variant: str
    quantity: int = Field(..., gt=0, description="Quantity must be at least 1")
    price_per_qty: float = Field(..., ge=0, description="Price cannot be negative")

    @computed_field
    @property
    # Compute subtotal
    def subtotal(self) -> float:
        """Automatically calculates quantity * price"""
        return float(self.quantity * self.price_per_qty)
    
    @model_validator(mode='after')
    def validate_price_integrity(self):
        """Ensures the price submitted matches the Matrix."""
        expected_price = PRODUCT_PRICES.get(self.product_name, {}).get(self.variant)
        
        if expected_price is None:
            raise ValueError(f"No price defined for {self.product_name} - {self.variant}")
            
        if self.price_per_qty != expected_price:
            raise ValueError(f"Price mismatch! Expected {expected_price}, got {self.price_per_qty}")
            
        return self

class Address(BaseModel):
    region: str
    province: str
    city: str
    barangay: str
    street: str
    unit_no: Optional[str] = None

# --- MAIN DATA CONTRACT ---
class OrderModel(BaseModel):
    customer_name: str = Field(..., min_length=2)
    # Regex enforces exactly 11 digits starting with 09, or +639 format
    contact_number: str = Field(..., pattern=r"^(09|\+639)\d{9}$")
    facebook_name: Optional[str] = None
    
    order_type: OrderType
    # Address is optional because Pick-up orders don't need one
    address: Optional[Address] = None 
    
    # Ensures the order has at least 1 item
    items: List[OrderItem] = Field(..., min_length=1) 
    
    preferred_date: date
    preferred_time: time
    notes: Optional[str] = None

    # --- CUSTOM VALIDATORS ---

    @field_validator('preferred_date')
    @classmethod
    def validate_lead_time(cls, v: date):
        """Forces the customer to choose a date at least 2 days from today."""
        min_date = date.today() + timedelta(days=2)
        if v < min_date:
            raise ValueError(f"Orders require a 2-day lead time. Earliest available date is {min_date}.")
        return v

    @model_validator(mode='after')
    def check_address_for_delivery(self):
        """Ensures an address is provided ONLY if the order is for Delivery."""
        if self.order_type == OrderType.DELIVERY and self.address is None:
            raise ValueError("A complete address is required for Delivery orders.")
        return self