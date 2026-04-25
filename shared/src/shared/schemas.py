from pydantic import BaseModel, Field, field_validator, model_validator
from typing import List, Optional
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

# --- NESTED MODELS ---
class OrderItem(BaseModel):
    product_name: BakeryProduct
    variant: Optional[str] = Field(None, description="e.g., Cheese, Chocolate, Classic")
    quantity: int = Field(..., gt=0, description="Quantity must be at least 1")
    price_per_qty: float = Field(..., ge=0, description="Price cannot be negative")

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