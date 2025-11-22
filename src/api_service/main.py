"""
API Service Main Application.

FastAPI application that provides REST and WebSocket endpoints for the Order API.

similar to @SpringBootApplication in Spring Boot, this is the entry point that configures and starts the web server.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio
import os
from shared import create_redis_client
from .routes import orders, trades
from .websockets import websocket_handlers
from .websockets.manager import ConnectionManager
from .services.order_producer import OrderProducer
from .services.event_subscriber import EventSubscriber
from .services.db_client import DatabaseClient


# Global instances (similar to @Autowired beans in Spring)
redis_client = None
connection_manager = None
order_producer = None
event_subscriber = None
db_client = None
subscriber_task = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown.
    
    This replaces @PostConstruct and @PreDestroy in Spring Boot.
    Runs on application startup and shutdown.
    """
    # Startup
    print("=" * 60)
    print("API Service Starting...")
    print("=" * 60)
    
    global redis_client, connection_manager, order_producer, event_subscriber, db_client, subscriber_task
    
    # Initialize Redis client
    print("[INIT] Connecting to Redis...")
    redis_client = await create_redis_client()
    print("[INIT] Redis connected")
    
    # Initialize database client
    print("[INIT] Connecting to database...")
    db_client = DatabaseClient()
    await db_client.connect()
    
    # Initialize WebSocket connection manager
    print("[INIT] Initializing WebSocket manager...")
    connection_manager = ConnectionManager()
    
    # Initialize order producer
    print("[INIT] Initializing order producer...")
    order_producer = OrderProducer(redis_client)
    
    # Initialize event subscriber
    print("[INIT] Initializing event subscriber...")
    event_subscriber = EventSubscriber(redis_client, connection_manager)
    
    # Inject dependencies into routes (similar to Spring's dependency injection)
    orders.order_producer_instance = order_producer
    orders.db_client_instance = db_client
    trades.db_client_instance = db_client
    websocket_handlers.connection_manager_instance = connection_manager
    
    # Start event subscriber in background
    print("[INIT] Starting event subscriber...")
    subscriber_task = asyncio.create_task(event_subscriber.start())
    
    print("=" * 60)
    print("API Service Ready!")
    print("API Documentation: http://localhost:8000/docs")
    print("=" * 60)
    
    # Yield control to the application
    yield
    
    # Shutdown process begin after yield
    print("\n[SHUTDOWN] API Service shutting down...")
    
    # Stop event subscriber
    if event_subscriber:
        await event_subscriber.stop()
    
    # Cancel subscriber task
    if subscriber_task:
        subscriber_task.cancel()
        try:
            await subscriber_task
        except asyncio.CancelledError:
            pass
    
    # Close Redis connection
    if redis_client:
        await redis_client.close()
    
    # Close database connection
    if db_client:
        await db_client.disconnect()
    
    print("[SHUTDOWN] API Service stopped")


# Create FastAPI application
# This is similar to @SpringBootApplication and creating the application context
app = FastAPI(
    title="Order API",
    description="RESTful API for order management with real-time WebSocket updates",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware (similar to @CrossOrigin in Spring Boot)
# Allow all origins for development (in production, we can specify allowed origins/ IPs)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers (similar to registering controllers in Spring Boot)
app.include_router(orders.router)
app.include_router(trades.router)
app.include_router(websocket_handlers.router)


# Root endpoint
@app.get("/", tags=["health"])
async def root():
    """
    Health check endpoint.
    
    Similar to a Spring Boot Actuator health endpoint.
    """
    stats = connection_manager.get_stats() if connection_manager else {}
    
    return {
        "status": "running",
        "service": "Order API",
        "version": "1.0.0",
        "websocket_connections": stats,
        "docs": "/docs"
    }


# Main entry point
if __name__ == "__main__":
    import uvicorn
    
    # Get configuration from environment
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    
    # Run the application
    # like SpringApplication.run() in Spring Boot
    uvicorn.run(
        "api_service.main:app",
        host=host,
        port=port,
        reload=False,  # could be set to True for development
        log_level="info"
    )
