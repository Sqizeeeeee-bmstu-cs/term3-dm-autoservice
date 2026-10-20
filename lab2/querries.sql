-- 1
SELECT * FROM Service;

-- 2
SELECT name, price FROM Service;

-- 3
SELECT admin_id, last_name, first_name
FROM Administrator
ORDER BY last_name;

-- 4
SELECT master_id, last_name, first_name
FROM Master
ORDER BY last_name
LIMIT 5 OFFSET 2;

-- 5
SELECT name, price
FROM Service
WHERE price BETWEEN 2000 AND 3000;


-- 6
SELECT vin, gos_number, model_id
FROM Automobile
WHERE model_id IN (
    SELECT model_id 
    FROM Model 
    WHERE brand IN ('BMW', 'AUDI')
);

-- 7
SELECT name, price, service_id
FROM Service
WHERE name LIKE 'Замена%'
ORDER BY name
LIMIT 10;

-- 8
SELECT first_name, last_name
FROM Administrator
WHERE middle_name IS NULL
ORDER BY last_name;

-- 9
SELECT COUNT(service_id) AS total_services, MAX(price) AS max_price, MIN(price) AS min_price, AVG(price) AS avg_price
FROM Service;


-- 10
SELECT master_id, COUNT(order_number) AS total_orders
FROM Work_Order
GROUP BY master_id
HAVING COUNT(order_number) > 3;

-- 11
SELECT a.vin, a.gos_number, c.last_name, c.first_name
FROM Automobile a
INNER JOIN Client c ON a.client_id = c.client_id;


-- 12
SELECT DISTINCT brand 
FROM Model;

-- 13
SELECT c.client_id, c.last_name, c.first_name
FROM Client c
WHERE EXISTS (
    SELECT 1 
    FROM Automobile a
    INNER JOIN Work_Order wo ON a.vin = wo.vin
    WHERE a.client_id = c.client_id
);

-- 14
SELECT name, price,
       CASE 
           WHEN price < 1000 THEN 'Бюджетная деталь'
           WHEN price BETWEEN 1000 AND 5000 THEN 'Средняя стоимость'
           ELSE 'Дорогая деталь'
       END AS price_category
FROM Part;


-- 17 part 1
SELECT order_number, vin, status, start_date
FROM Work_Order
WHERE end_date IS NULL;


-- 17 part 2
SELECT name AS part_group, AVG(price) AS average_price
FROM Part
GROUP BY name
ORDER BY average_price DESC
LIMIT 1;
