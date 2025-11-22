# Request/Response models using Pydantic (like @Valid in Spring)

from pydantic import BaseModel, Field


class CreateOrderRequestAPI(BaseModel):
    """
    request model for creating an order.

    inbuilt Pydantic automatically validates the request body,
    similar to @Valid @RequestBody in Spring Boot.
    """
    quantity: int = Field(gt=0, description="Order quantity (must be > 0)")
    price: float = Field(gt=0, description="Order price (must be > 0)")
    side: int = Field(ge=-1, le=1, description="Order side: 1 for buy, -1 for sell")

    """
    helps with documentation, like @Schema(example="...")
    """

    class Config:
        json_schema_extra = {
            "example": {
                "quantity": 100,
                "price": 123.45,
                "side": 1
            }
        }


class ModifyOrderRequestAPI(BaseModel):
    """Request model for modifying an order"""
    updated_price: float = Field(gt=0, description="New price (must be > 0)")

    """
    helps with documentation, like @Schema(example="...")
    """

    class Config:
        json_schema_extra = {
            "example": {
                "updated_price": 125.00
            }
        }


class CreateOrderResponse(BaseModel):
    """response model for order creation"""
    order_id: str


class OperationResponse(BaseModel):
    """generic boolean response for operations"""
    success: bool
