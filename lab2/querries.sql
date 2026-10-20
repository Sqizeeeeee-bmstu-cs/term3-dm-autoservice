

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
SELECT 



