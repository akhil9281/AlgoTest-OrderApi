"""
Order REST endpoints.

Provides CRUD operations for orders.
Similar to @RestController in Spring Boot.
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, status, Depends

from ..dtos.order_dtos import *
from ..services.order_producer import OrderProducer

# Create router (like @RequestMapping in Spring)
router = APIRouter(
    prefix="/orders",
    tags=["orders"]
)


# dependency injection helpers
# like @Autowired In Spring Boot, here we use Depends()
order_producer_instance: Optional[OrderProducer] = None
db_client_instance = None


def get_order_producer() -> OrderProducer:
    """
    Dependency provider for OrderProducer.
    
    Similar to @Autowired in Spring Boot.
    This will be injected by FastAPI's dependency injection.
    """
    if order_producer_instance is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Order producer not initialized"
        )
    return order_producer_instance


def get_db_client():
    """Dependency provider for DatabaseClient"""
    if db_client_instance is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database client not initialized"
        )
    return db_client_instance


# REST Endpoints

@router.post("/", response_model=CreateOrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    request: CreateOrderRequestAPI,
    producer: OrderProducer = Depends(get_order_producer)
):
    """
    creates a new order.
    
    Similar to: @PostMapping("/orders")
    """
    try:
        # validate price precision (must be multiple of 0.01)
        if round(request.price, 2) != request.price:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Price must be a multiple of 0.01"
            )
        
        # validate side
        if request.side not in [1, -1]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Side must be 1 (buy) or -1 (sell)"
            )
        
        # convert price to paise (cents) -> can be a utils
        price_paise = int(round(request.price * 100))
        
        # send to queue via producer
        order_id = await producer.create_order(
            quantity=request.quantity,
            price_paise=price_paise,
            side=request.side
        )
        
        return CreateOrderResponse(
            order_id=order_id
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating order: {str(e)}"
        )


@router.put("/{order_id}", response_model=OperationResponse)
async def modify_order(
    order_id: str,
    request: ModifyOrderRequestAPI,
    producer: OrderProducer = Depends(get_order_producer)
):
    """
    modify an existing order's price.
    
    similar to: @PutMapping("/orders/{orderId}")
    """
    try:
        # Validate price precision
        if round(request.updated_price, 2) != request.updated_price:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Price must be a multiple of 0.01"
            )
        
        # Convert price to paise
        updated_price_paise = int(round(request.updated_price * 100))
        
        # Send modification request to queue
        await producer.modify_order(order_id, updated_price_paise)
        
        return OperationResponse(
            success=True
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error modifying order: {str(e)}"
        )


@router.delete("/{order_id}", response_model=OperationResponse)
async def cancel_order(
    order_id: str,
    producer: OrderProducer = Depends(get_order_producer)
):
    """
    cancel an order.
    
    similar to: @DeleteMapping("/orders/{orderId}")
    """
    try:
        # Send cancellation request to queue
        await producer.cancel_order(order_id)
        
        return OperationResponse(
            success=True
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error cancelling order: {str(e)}"
        )


@router.get("/{order_id}")
async def get_order(
    order_id: str,
    db_client = Depends(get_db_client)
):
    """
    get a specific order by ID.
    
    queries the database for order details.
    """
    try:
        order_data = await db_client.get_order(order_id)
        
        if not order_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Order {order_id} not found"
            )
        
        # convert paise to float for API response
        return {
            "order_id": order_data["order_id"],
            "side": "BUY" if order_data["side"] == 1 else "SELL",
            "price": order_data["price_paise"] / 100.0,
            "original_qty": order_data["original_qty"],
            "traded_qty": order_data["traded_qty"],
            "avg_traded_price": order_data["avg_traded_price_paise"] / 100.0 if order_data["avg_traded_price_paise"] else 0.0,
            "status": order_data["status"],
            "created_at": order_data["created_at"],
            "updated_at": order_data["updated_at"]
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching order: {str(e)}"
        )


@router.get("/")
async def get_all_orders(db_client = Depends(get_db_client)):
    """
    get all orders.
    
    returns the last 100 orders from the database.
    """
    try:
        orders_data = await db_client.get_all_orders()
        
        # Convert paise to float for API response
        return {
            "orders": [
                {
                    "order_id": order["order_id"],
                    "side": "BUY" if order["side"] == 1 else "SELL",
                    "price": order["price_paise"] / 100.0,
                    "original_qty": order["original_qty"],
                    "traded_qty": order["traded_qty"],
                    "avg_traded_price": order["avg_traded_price_paise"] / 100.0 if order["avg_traded_price_paise"] is not None else 0.0,
                    "status": order["status"],
                    "created_at": order["created_at"],
                    "updated_at": order["updated_at"]
                }
                for order in orders_data
            ],
            "count": len(orders_data)
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching orders: {str(e)}"
        )
