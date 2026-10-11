PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS Status_Change;
DROP TABLE IF EXISTS Part_Position;
DROP TABLE IF EXISTS Order_Service;
DROP TABLE IF EXISTS Work_Order;
DROP TABLE IF EXISTS Model_Part_Compatibility;
DROP TABLE IF EXISTS Part;
DROP TABLE IF EXISTS Automobile;
DROP TABLE IF EXISTS Model;
DROP TABLE IF EXISTS Client_Phone;
DROP TABLE IF EXISTS Client;
DROP TABLE IF EXISTS Service;
DROP TABLE IF EXISTS Master;
DROP TABLE IF EXISTS Administrator;

-- Administrator
CREATE TABLE Administrator (
    admin_id INTEGER NOT NULL,
    last_name TEXT NOT NULL,
    first_name TEXT NOT NULL,
    middle_name TEXT,
    CONSTRAINT Administrator_PK PRIMARY KEY (admin_id)
);

-- Master
CREATE TABLE Master (
    master_id INTEGER NOT NULL,
    last_name TEXT NOT NULL,
    first_name TEXT NOT NULL,
    middle_name TEXT,
    CONSTRAINT Master_PK PRIMARY KEY (master_id)
);

-- Service
CREATE TABLE Service (
    service_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    price REAL NOT NULL CHECK (price >= 0),
    CONSTRAINT Service_PK PRIMARY KEY (service_id)
);

-- Client
CREATE TABLE Client (
    client_id INTEGER NOT NULL,
    last_name TEXT NOT NULL,
    first_name TEXT NOT NULL,
    middle_name TEXT,
    CONSTRAINT Client_PK PRIMARY KEY (client_id)
);

-- Client_Phone
CREATE TABLE Client_Phone (
    client_id INTEGER NOT NULL,
    phone TEXT NOT NULL,
    CONSTRAINT Client_Phone_PK PRIMARY KEY (client_id, phone),
    CONSTRAINT Client_Phone_FK FOREIGN KEY (client_id)
        REFERENCES Client (client_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);

-- Model
CREATE TABLE Model (
    model_id INTEGER NOT NULL,
    brand TEXT NOT NULL,
    model_name TEXT NOT NULL,
    CONSTRAINT Model_PK PRIMARY KEY (model_id),
    CONSTRAINT Model_UQ UNIQUE (brand, model_name)
);

-- Automobile
CREATE TABLE Automobile (
    vin TEXT NOT NULL,
    gos_number TEXT NOT NULL,
    client_id INTEGER NOT NULL,
    model_id INTEGER NOT NULL,
    CONSTRAINT Automobile_PK PRIMARY KEY (vin),
    CONSTRAINT Automobile_GosNumber_UQ UNIQUE (gos_number),
    CONSTRAINT Automobile_Client_FK FOREIGN KEY (client_id)
        REFERENCES Client (client_id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,
    CONSTRAINT Automobile_Model_FK FOREIGN KEY (model_id)
        REFERENCES Model (model_id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE
);

-- Part
CREATE TABLE Part (
    article TEXT NOT NULL,
    name TEXT NOT NULL,
    price REAL NOT NULL CHECK (price >= 0),
    stock INTEGER NOT NULL DEFAULT 0 CHECK (stock >= 0),
    CONSTRAINT Part_PK PRIMARY KEY (article)
);

-- Model_Part_Compatibility
CREATE TABLE Model_Part_Compatibility (
    model_id INTEGER NOT NULL,
    article TEXT NOT NULL,
    CONSTRAINT Model_Part_Compatibility_PK PRIMARY KEY (model_id, article),
    CONSTRAINT MPC_Model_FK FOREIGN KEY (model_id)
        REFERENCES Model (model_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    CONSTRAINT MPC_Part_FK FOREIGN KEY (article)
        REFERENCES Part (article)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);

-- Work_Order
CREATE TABLE Work_Order (
    order_number INTEGER NOT NULL,
    vin TEXT NOT NULL,
    admin_id INTEGER NOT NULL,
    master_id INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'в работе'
        CHECK (status IN ('в работе', 'ожидает запчасти', 'готов', 'выдан', 'отменён')),
    start_date TEXT NOT NULL DEFAULT (date('now')),
    planned_date TEXT,
    end_date TEXT,
    malfunction TEXT,
    CONSTRAINT Work_Order_PK PRIMARY KEY (order_number),
    CONSTRAINT Work_Order_Dates_CK CHECK (
        (planned_date IS NULL OR planned_date >= start_date)
        AND (end_date IS NULL OR end_date >= start_date)
    ),
    CONSTRAINT Work_Order_Automobile_FK FOREIGN KEY (vin)
        REFERENCES Automobile (vin)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,
    CONSTRAINT Work_Order_Admin_FK FOREIGN KEY (admin_id)
        REFERENCES Administrator (admin_id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,
    CONSTRAINT Work_Order_Master_FK FOREIGN KEY (master_id)
        REFERENCES Master (master_id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE
);

-- Status_Change
CREATE TABLE Status_Change (
    change_id INTEGER NOT NULL,
    order_number INTEGER NOT NULL,
    status TEXT NOT NULL
        CHECK (status IN ('в работе', 'ожидает запчасти', 'готов', 'выдан', 'отменён')),
    changed_at TEXT NOT NULL DEFAULT (datetime('now')),
    CONSTRAINT Status_Change_PK PRIMARY KEY (change_id),
    CONSTRAINT Status_Change_Order_FK FOREIGN KEY (order_number)
        REFERENCES Work_Order (order_number)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);

-- Order_Service
CREATE TABLE Order_Service (
    order_number INTEGER NOT NULL,
    service_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1 CHECK (quantity > 0),
    CONSTRAINT Order_Service_PK PRIMARY KEY (order_number, service_id),
    CONSTRAINT Order_Service_WorkOrder_FK FOREIGN KEY (order_number)
        REFERENCES Work_Order (order_number)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    CONSTRAINT Order_Service_Service_FK FOREIGN KEY (service_id)
        REFERENCES Service (service_id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE
);

-- Part_Position
CREATE TABLE Part_Position (
    order_number INTEGER NOT NULL,
    position_number INTEGER NOT NULL,
    article TEXT NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1 CHECK (quantity > 0),
    CONSTRAINT Part_Position_PK PRIMARY KEY (order_number, position_number),
    CONSTRAINT Part_Position_WorkOrder_FK FOREIGN KEY (order_number)
        REFERENCES Work_Order (order_number)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    CONSTRAINT Part_Position_Part_FK FOREIGN KEY (article)
        REFERENCES Part (article)
        ON DELETE RESTRICT
        ON UPDATE CASCADE
);
