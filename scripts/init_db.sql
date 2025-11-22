-- Order API Database Schema

-- Orders table
CREATE TABLE IF NOT EXISTS orders (
    id VARCHAR(36) PRIMARY KEY,
    side SMALLINT NOT NULL CHECK (side IN (1, -1)),  -- 1 for buy, -1 for sell
    order_price INT NOT NULL CHECK (order_price > 0),  -- Price in paise (cents)
    order_quantity INT NOT NULL CHECK (order_quantity > 0),
    avg_traded_price INT DEFAULT NULL,  -- Average execution price
    traded_quantity INT DEFAULT 0 CHECK (traded_quantity >= 0),
    status VARCHAR(20) DEFAULT 'OPEN',  -- OPEN, PARTIALLY_FILLED, FILLED, CANCELLED
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Trades table
CREATE TABLE IF NOT EXISTS trades (
    id VARCHAR(36) PRIMARY KEY,
    bid_order_id VARCHAR(36) NOT NULL,
    ask_order_id VARCHAR(36) NOT NULL,
    traded_price INT NOT NULL CHECK (traded_price > 0),
    traded_quantity INT NOT NULL CHECK (traded_quantity > 0),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (bid_order_id) REFERENCES orders(id),
    FOREIGN KEY (ask_order_id) REFERENCES orders(id)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_orders_side ON orders(side);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_trades_created_at ON trades(created_at);
