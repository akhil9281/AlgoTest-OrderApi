# ED for Assessment POC - Order API

## Requirements:
1. Fast order matching in  amortized O(1) time (per order, per trade-matching)
2. Exposed API's for CRUD Order Operation. Replicating an exchange, our API should be able to handle load in concurrent situations as well.
3. Snapshots of the order book - live orders only.
3. Crash recovery system - CRS
4. Dockerized application
    - Implement volume to store previous state
    - Will work in conjunction with the 'CRS' to recover to the last state.


## High Level Flow:
- Since it is specifically mentioned that order matching be done in amortized O(1) time and we need to implement a Data Structure, we need some kind of in-memory storage to store the order book and trades data, to maximize throughput.
- We will need a separate async microservice for the persistence layer. This will handle DB persistence.
- To handle concurrent requests and implement horizontal scaling, we need to have a API microservices, which will expose stateless REST API endpoints.

                REST API Microservice (AM)
                - data validation
                - data mapping to DTO
                - WebSocket handlers (trades, orderbook snapshots)
                        |
                        | Redis Streams (order_queue)
                        |
                        ▼
                Order Book Microservice (OBM)
                [SINGLE instance - sequential processing]
                - Order matching engine
                - In-memory state of the order book 
                - Trade execution 
                - Period snapshot at every 1 sec
                - WAL append and CRS
                        |                                     |      
                        | Async tasks                         | Redis Pub/Sub
                        |                                     | (trade events, snapshots)
                        ▼                                     ▼
                Persistence Layer (PL)                       API Microservice (AM)
                - Async DB writes                            - Broadcasts to WebSocket clients
                - Off critical path
                        |
                        ▼
                    DB Layer
                (PostgreSQL / MySQL)


## Service Flow
- AM will receive the request, upon receiving the request:
    - AM will run simple validation logic based on business requirements.
    - Map request-data into relevant DTOs. Convert price in PUT/POST requests to INT from FLOAT by multiplication by 100 to prevent data-inconsistency in lossy conversion.
    - Push message to Redis Streams 'order_queue'
    - WebSocket handlers in AM subscribe to Redis Pub/Sub for trade events and snapshots, then broadcast to connected clients.

- The order_queue (Redis Streams) message will be consumed by OBM (single consumer), which will:
    - Implement a Data Structure with O(1) save and fetch time complexity.
    - Upon receiving the POST request data for order, assign an 'order_id' using 'UUID'
    - Store or update the request-data in respective list - Buy or Sell.
    - Append the CRUD log to the WAL, if not a read request.
    - Perform order matching logic for trade execution.
    - Execute Trade if match found:
        - choose the trade quantity as the min of SELL or BUY order.
        - choose the trade price as the price present in the memory instead of the request-price
        - calculate avg traded price and traded quantity as well as order alive status for the existing entry in our order book and update the respective values for the same.
        - create trade entry and append to WAL
        - create updated avg trade price and traded quantity log in WAL for the request-order.
        - Publish trade event to Redis Pub/Sub (channel: 'trade_events')
    - Background task publishes order book snapshots every 1 second to Redis Pub/Sub (channel: 'snapshot_events')
    - Trigger async tasks for PL to persist data.

- The PL will persist the data into our DB asynchronously.
  - Tech used - asyncio with asyncpg/aiomysql for async DB operations


## DTOs and Payloads:
1. OrderRecord :
```
{
  "order_id": "uuid",
  "side": 1,         // 1 buy, -1 sell
  "price_paise": 1234, // int
  "original_qty": 100, // int
  "remaining_qty": 60, // int
  "traded_qty": 40, // int
  "status": "OPEN|PARTIALLY_FILLED|FILLED|CANCELLED",
  "created_timestamp": "...", // timestamp
  "updated_timestamp": "..." // tiemstamp
}
```

2. TradeRecord:
```
{
  "trade_id": "uuid",
  "timestamp": "...",
  "price_paise": 12000,
  "qty": 20,
  "bid_order_id": "...",
  "ask_order_id": "..."
}
```

3. Incoming Order Request:
```
{
  "quantity": int, // value > 0
  "price": float, // value > 0, multiple of 0.01
  "side": bool, // (1) for buy, (-1) for sell
}
```

4. Order Fetch DTO:
```
{
  "order_price": float,
  "order_quantity": int,
  "average_traded_price": float,
  "traded_quantity": int,
  "order_alive": bool // order_quantity - traded_quantity > 0
}
```

5. Trade Fetch DTO:
```
{
  "unique_id": "uuid",
  "execution_timestamp": timstamp,
  "price": float,
  "qty": int, // value > 0
  "bid_order_id": "uuid",
  "ask_order_id": "uuid"
}
```


6. order_queue Message:
```
{
  "unique_id": "uuid",
  "execution_timestamp": timstamp,
  "payload": {
    "request": POST, // GET | POST | PUT | DEL
    "data": OrderRecord // relevent DTO for the request type
    }
}
```

7. data_pipeline Message:
```
{
  "unique_id": "uuid",
  "execution_timestamp": timstamp,
  "table": ORDER | TRADE,
  "payload": {Relevent DTO} // OrderRecord | TradeRecord
}
```

8. WAL Message:
```
{
  "lsn": 12345, // index of WAL entry
  "timestamp": "2025-11-19T01:21:00Z", // timestamp of creating WAL entry
  "operation_type": "INSERT", // INSERT | UPDATE | DELETE
  "table_name": "ORDER", // ORDER | TRADE
  "data": { // relevent Dto or data
    "id": 1,
    "name": "Laptop",
    "price": 1200.00
  },
  "transaction_id": "uuid" // optional
}
```


## DB Schema:
```
table 'order' {
    "id": 'uuid' // primary key
    "order_quantity": int, // value > 0
    "order_price": int, // greater than 01
    "avg_traded_price": int, // default null
    "traded_quantity": int, // default 0
    "side": bool, // (1) for buy, (-1) for sell
    "created_timestamp": current_timestamp, // non-null
    "updated_timestamp": current_timestamp ON UPDATE current_timestamp, // non-null
}

table 'trade' {
    "id": 'uuid' // primary key
    "buy_order_id": 'uuid', // non-null
    "sell_order_id": 'uuid', // non-null
    "traded_price": int, // default null
    "traded_quantity": int, // value > 0
    "created_timestamp": current_timestamp, // non-null
    "updated_timestamp": current_timestamp ON UPDATE current_timestamp, // non-null
}
```

## Current Scope:
 - **Message Queue**: Redis Streams for order_queue (persistent, ordered delivery)
 - **Event Broadcasting**: Redis Pub/Sub for trade events and order book snapshots
 - **Microservice architecture**: API Service (scalable) + OBM Service (single instance) + Redis + Database
 - **Dockerization**: Multi-container setup with docker-compose
 - **WAL for Crash Recovery System**: File-based WAL with recovery logic on OBM startup

### Backend and Business Logic:
- Modify semantics: the order_id stays the same but we will treat it as new with renewed time priority.
- WAL as file: we will use WAL for now. maybe implement DB once MVP is functional.
- Trades persistence: async in nature.. matching will happen in real-time with immediate WAL append and save trade in-memory only with and then websocket reply using async persistence microservice after data is persisted in DB.
- Order-matching logic:
  - Orders are matched at best price first.
  - At the same price level, FIFO rule is applied
- Trade Matching Flow:
  - New order comes with price P.
  - Check for best ASK price (lowest ASK price).
  - if P >= best_ask_price, match the order.
    - trade price = ASK price (existing price in orderbook)
    - trade quantity = min (order_quantity, ask_quantity)
    - update avg_trade_price for both the orders, by simply taking average of their previous avg_trade_price*traded_quantity to the trade price and quantity of the current trade.
    - update traded_quantity for both the orders.
    - update the active_status for both the orders in the orderBook and remove the order from the orderbook if the traded_quantity == order_quantity.
- Order Book data structure:
  - Using `sortedcontainers.SortedDict` + `collections.deque`.
  - BUY list - sorted by price in descending order.
  - SELL list - sorted by price in ascending order.
  - Each price level will have a deque of orders, arranged in FIFO manner.
- Price handling:
  - We will accept the price as float, as per the requirements.
  - But all the processing and storage of data will be done in int, by converting the price to paise by multiplying with 100.
  - This is to avoid any precision issues due to floating point.

### Docker Implementation:
- **Multi-container setup** using docker-compose:
  - API Service container (FastAPI)
  - OBM Service container (Python)
  - Redis container (redis:alpine)
  - Database container (PostgreSQL/MySQL)
- **Volumes** for persistent data:
  - WAL file storage (mounted to OBM container)
  - Database data (mounted to DB container)
- **Networking**: Services communicate via Docker internal network and Redis
- **Environment variables**: Database URLs, Redis URLs configured via .env file


### Personal Note: Things to learn:
Since I am new to Python and Python based development in general, I will need to learn the following things:
- Python OOPS.
- Python microservice development
- Python in-built data structures.. such as SortedDict + deque
- Redis integration (Streams for queues, Pub/Sub for events)
- Dockerizing Python app with multi-container orchestration
- Python build script to install dependencies and create WAL and metadata.json for `lsn` value for CRS.
- WAL implementation and crash recovery logic
- Database setup (PostgreSQL/MySQL) and linking with Python Project - async DB operations















