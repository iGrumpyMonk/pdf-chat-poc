
-- SIMPLE MyShop database for the assignment
-- Exactly 3 tables: Products, Orders, OrderItems
-- Minimal/common fields only

IF DB_ID('MyShop') IS NULL
BEGIN
    CREATE DATABASE MyShop;
END
GO

USE MyShop;
GO

-- Drop (child → parent) if they exist
IF OBJECT_ID('dbo.OrderItems','U') IS NOT NULL DROP TABLE dbo.OrderItems;
IF OBJECT_ID('dbo.Orders','U')     IS NOT NULL DROP TABLE dbo.Orders;
IF OBJECT_ID('dbo.Products','U')   IS NOT NULL DROP TABLE dbo.Products;
GO

-- 1) Products (common fields)
CREATE TABLE dbo.Products(
    product_id INT IDENTITY(1,1) PRIMARY KEY,
    name       NVARCHAR(200) NOT NULL,
    price      DECIMAL(10,2) NOT NULL
);
GO

-- 2) Orders (common fields)
CREATE TABLE dbo.Orders(
    order_id      INT IDENTITY(1,1) PRIMARY KEY,
    customer_name NVARCHAR(200) NOT NULL,
    order_date    DATETIME NOT NULL
);
GO

-- 3) OrderItems (common fields)
CREATE TABLE dbo.OrderItems(
    order_item_id INT IDENTITY(1,1) PRIMARY KEY,
    order_id      INT NOT NULL FOREIGN KEY REFERENCES dbo.Orders(order_id) ON DELETE CASCADE,
    product_id    INT NOT NULL FOREIGN KEY REFERENCES dbo.Products(product_id),
    quantity      INT NOT NULL CHECK (quantity > 0),
    unit_price    DECIMAL(10,2) NOT NULL
);
GO

-- Seed 5 products
INSERT INTO dbo.Products (name, price) VALUES
('Apple Watch Band', 19.99),
('USB-C Cable 1m',    7.49),
('Wireless Mouse',   24.90),
('Mechanical Keyboard', 79.00),
('27"" 4K Monitor',  329.00);
GO

-- Seed 9 orders across the 3 dates requested
INSERT INTO dbo.Orders (customer_name, order_date) VALUES
-- 23rd Aug 2025
(N'Sana Khan',    '2025-08-23T10:15:00'),
(N'Alex Li',      '2025-08-23T14:45:00'),
(N'Omar Haddad',  '2025-08-23T18:30:00'),
-- 24th Aug 2025
(N'Priya Sharma', '2025-08-24T09:05:00'),
(N'James O''Neil','2025-08-24T13:20:00'),
(N'Fatima Noor',  '2025-08-24T20:10:00'),
-- 25th Aug 2025
(N'Lucas Kim',    '2025-08-25T08:55:00'),
(N'Maya Chen',    '2025-08-25T12:30:00'),
(N'Ola Al-Farsi', '2025-08-25T16:40:00');
GO

-- Seed order items (1–2 lines per order), using current product prices
INSERT INTO dbo.OrderItems (order_id, product_id, quantity, unit_price) VALUES
-- Order 1
(1, 1, 2, 19.99), (1, 2, 1, 7.49),
-- Order 2
(2, 5, 1, 329.00),
-- Order 3
(3, 3, 1, 24.90), (3, 4, 1, 79.00),
-- Order 4
(4, 2, 3, 7.49),
-- Order 5
(5, 4, 1, 79.00), (5, 1, 1, 19.99),
-- Order 6
(6, 3, 2, 24.90),
-- Order 7
(7, 5, 1, 329.00), (7, 2, 1, 7.49),
-- Order 8
(8, 1, 4, 19.99),
-- Order 9
(9, 4, 1, 79.00), (9, 2, 1, 7.49), (9, 3, 1, 24.90);
GO

-- Quick checks
SELECT 'Products' AS what, COUNT(*) AS cnt FROM dbo.Products
UNION ALL
SELECT 'Orders',   COUNT(*) FROM dbo.Orders
UNION ALL
SELECT 'Items',    COUNT(*) FROM dbo.OrderItems;

-- Orders per date (should show 3 per day)
SELECT CONVERT(date, order_date) AS order_day, COUNT(*) AS orders_count
FROM dbo.Orders
GROUP BY CONVERT(date, order_date)
ORDER BY order_day;

-- Simple joined listing
SELECT o.order_id, o.customer_name, o.order_date, p.name AS product, i.quantity, i.unit_price,
       i.quantity * i.unit_price AS line_total
FROM dbo.OrderItems i
JOIN dbo.Orders   o ON o.order_id = i.order_id
JOIN dbo.Products p ON p.product_id = i.product_id
ORDER BY o.order_date, o.order_id, i.order_item_id;
GO
