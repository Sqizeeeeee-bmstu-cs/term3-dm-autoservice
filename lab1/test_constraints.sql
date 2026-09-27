-- ЭТАП 1: Наполнение таблиц корректными тестовыми данными
PRAGMA foreign_keys = ON;

-- Administrator
INSERT INTO Administrator (admin_id, fio) VALUES
    (1, 'Иванов Иван Иванович'),
    (2, 'Петрова Анна Сергеевна');

-- Master
INSERT INTO Master (master_id, fio) VALUES
    (1, 'Сидоров Пётр Николаевич'),
    (2, 'Кузнецов Олег Викторович');

-- Service
INSERT INTO Service (service_id, name, price) VALUES
    (1, 'Замена масла', 1500.00),
    (2, 'Диагностика ходовой', 2000.00),
    (3, 'Шиномонтаж', 1200.00);

-- Client
INSERT INTO Client (client_id, fio) VALUES
    (1, 'Смирнов Алексей Дмитриевич'),
    (2, 'Волкова Мария Игоревна');

-- Client_Phone
INSERT INTO Client_Phone (client_id, phone) VALUES
    (1, '+79161234567'),
    (1, '+79261234567'),
    (2, '+79031234567');

-- Model
INSERT INTO Model (model_id, brand, model_name) VALUES
    (1, 'Toyota', 'Camry'),
    (2, 'Kia', 'Rio');

-- Automobile
INSERT INTO Automobile (vin, gos_number, client_id, model_id) VALUES
    ('JT2BF22K1W0123456', 'А123ВС777', 1, 1),
    ('XW8ZZZ1KZBG654321', 'В456КМ777', 2, 2);

-- Part
INSERT INTO Part (article, name, price, stock) VALUES
    ('OIL-001', 'Масло моторное 5W-30', 2500.00, 50),
    ('FLT-002', 'Фильтр масляный', 450.00, 30),
    ('TIRE-003', 'Шина летняя 195/65 R15', 4500.00, 20);

-- Model_Part_Compatibility
INSERT INTO Model_Part_Compatibility (model_id, article) VALUES
    (1, 'OIL-001'),
    (1, 'FLT-002'),
    (2, 'OIL-001'),
    (2, 'TIRE-003');

-- Work_Order
INSERT INTO Work_Order (order_number, vin, admin_id, master_id, status, order_date, malfunction) VALUES
    (1, 'JT2BF22K1W0123456', 1, 1, 'в работе', '2026-09-20', 'Стук в подвеске'),
    (2, 'XW8ZZZ1KZBG654321', 2, 2, 'готов', '2026-09-22', NULL);

-- Order_Service
INSERT INTO Order_Service (order_number, service_id, quantity) VALUES
    (1, 2, 1),
    (2, 1, 1),
    (2, 3, 4);

-- Part_Position
INSERT INTO Part_Position (order_number, position_number, article, quantity) VALUES
    (1, 1, 'OIL-001', 1),
    (1, 2, 'FLT-002', 1),
    (2, 1, 'TIRE-003', 4);

-- Попытка вставить клиента без ФИО (fio NOT NULL)
INSERT INTO Client (client_id, fio) VALUES (3, NULL);


-- Попытка вставить автомобиль с уже существующим гос. номером
INSERT INTO Automobile (vin, gos_number, client_id, model_id) VALUES
    ('1HGCM82633A123456', 'А123ВС777', 2, 2);

-- Попытка создать автомобиль с несуществующим client_id
INSERT INTO Automobile (vin, gos_number, client_id, model_id) VALUES
    ('1HGCM82633A999999', 'Х999ХХ777', 999, 1);

-- 5.1 Попытка вставить запчасть с отрицательной ценой
INSERT INTO Part (article, name, price, stock) VALUES
    ('BAD-001', 'Бракованная деталь', -100.00, 5);

-- 5.2 Попытка создать заказ-наряд с недопустимым статусом
INSERT INTO Work_Order (order_number, vin, admin_id, master_id, status, order_date) VALUES
    (3, 'JT2BF22K1W0123456', 1, 1, 'непонятный_статус', '2026-09-27');

DELETE FROM Client WHERE client_id = 1;

-- Сначала проверим, что связанные записи есть
SELECT * FROM Order_Service WHERE order_number = 1;
SELECT * FROM Part_Position WHERE order_number = 1;

-- Удаляем заказ-наряд
DELETE FROM Work_Order WHERE order_number = 1;

-- Проверяем, что связанные записи удалились каскадно
SELECT * FROM Order_Service WHERE order_number = 1;
SELECT * FROM Part_Position WHERE order_number = 1;
