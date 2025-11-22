"""
Trade REST endpoints.

Provides read-only access to executed trades.
Similar to @RestController in Spring Boot.
"""

from fastapi import APIRouter, HTTPException, status, Depends
from typing import List


# Create router
router = APIRouter(
    prefix="/trades",
    tags=["trades"]
)

# Database client instance (injected from main)
db_client_instance = None


def get_db_client():
    """Dependency provider for DatabaseClient"""
    if db_client_instance is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database client not initialized"
        )
    return db_client_instance


@router.get("")
async def get_all_trades(db_client = Depends(get_db_client)):
    """
    get all executed trades.

    returns the latest 100 trades from the database.
    """
    try:
        trades_data = await db_client.get_all_trades()
        
        # Convert paise to float for API response
        return {
            "trades": [
                {
                    "trade_id": trade["trade_id"],
                    "bid_order_id": trade["bid_order_id"],
                    "ask_order_id": trade["ask_order_id"],
                    "price": trade["price_paise"] / 100.0,
                    "quantity": trade["qty"],
                    "timestamp": trade["timestamp"]
                }
                for trade in trades_data
            ],
            "count": len(trades_data)
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching trades: {str(e)}"
        )
