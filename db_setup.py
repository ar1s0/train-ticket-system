# db_setup.py

import mysql.connector
from mysql.connector import Error
from db_config import DB_CONFIG
from db_sample_data import insert_sample_data

def setup_database(drop_existing=True):
    """
    Sets up the database schema and objects
    
    Args:
        drop_existing (bool): If True, drops and recreates the database
    """
    db_name = DB_CONFIG['database']
    db_password = DB_CONFIG['password']
    db_port = DB_CONFIG['port']

    conn = None
    cursor = None
    try:
        # Initial connection without database
        conn = mysql.connector.connect(
            host=DB_CONFIG['host'],
            user=DB_CONFIG['user'],
            password=db_password,
            port=db_port
        )
        cursor = conn.cursor()

        # Database creation/drop logic
        if drop_existing:
            print(f"Dropping existing database '{db_name}'...")
            cursor.execute(f"DROP DATABASE IF EXISTS `{db_name}`")
        
        print(f"Creating database '{db_name}'...")
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}` DEFAULT CHARACTER SET 'utf8mb4'")
        
        # Close initial connection
        cursor.close()
        conn.close()

        # Reconnect to the specific database
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(buffered=True)
        
        # Execute statements with proper error handling
        try:
            # Tables
            create_tables(cursor)
            # Views
            create_views(cursor)
            # Indexes
            create_indexes(cursor)
            # Triggers
            create_triggers(cursor)
            # Procedures
            create_procedures(cursor)

            insert_sample_data()
            conn.commit()
            print("Database setup completed successfully!")
            return True
            
        except Error as err:
            conn.rollback()
            print(f"Error during database setup: {err}")
            return False
            
    except Error as e:
        print(f"Database connection error: {e}")
        return False
        
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

def create_tables(cursor):
    """Create all database tables"""
    table_statements = [
        """
        CREATE TABLE IF NOT EXISTS `Stations` (
            `station_id` INT PRIMARY KEY AUTO_INCREMENT,
            `station_name` VARCHAR(50) UNIQUE NOT NULL,
            `station_code` VARCHAR(10) UNIQUE NULL
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS `Trains` (
            `train_number` VARCHAR(10) PRIMARY KEY,
            `train_type` VARCHAR(20) NOT NULL,
            `total_seats` INT NOT NULL CHECK (`total_seats` >= 0),
            `departure_station_id` INT NOT NULL,
            `arrival_station_id` INT NOT NULL,
            FOREIGN KEY (`departure_station_id`) REFERENCES `Stations`(`station_id`),
            FOREIGN KEY (`arrival_station_id`) REFERENCES `Stations`(`station_id`)
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS `Stopovers` (
            `stopover_id` INT PRIMARY KEY AUTO_INCREMENT,
            `train_number` VARCHAR(10) NOT NULL,
            `station_id` INT NOT NULL,
            `start_date` DATE NOT NULL,
            `arrival_time` DATETIME NULL,
            `departure_time` DATETIME NULL,
            `stop_order` INT NOT NULL CHECK (`stop_order` > 0),
            `seats` INT NOT NULL CHECK (`seats` >= 0),
            `distance` INT NULL,
            FOREIGN KEY (`train_number`) REFERENCES `Trains`(`train_number`) ON DELETE CASCADE,
            FOREIGN KEY (`station_id`) REFERENCES `Stations`(`station_id`),
            UNIQUE (`train_number`, `station_id`, `start_date`)
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS `Prices` (
            `price_id` INT PRIMARY KEY AUTO_INCREMENT,
            `train_number` VARCHAR(10) NOT NULL,
            `departure_station_id` INT NOT NULL,
            `arrival_station_id` INT NOT NULL,
            `price_per_ten_miles` DECIMAL(10, 2) NOT NULL CHECK (`price_per_ten_miles` >= 0),
            FOREIGN KEY (`train_number`) REFERENCES `Trains`(`train_number`) ON DELETE CASCADE,
            FOREIGN KEY (`departure_station_id`) REFERENCES `Stations`(`station_id`),
            FOREIGN KEY (`arrival_station_id`) REFERENCES `Stations`(`station_id`),
            UNIQUE (`train_number`, `departure_station_id`, `arrival_station_id`)
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS `Customers` (
            `name` VARCHAR(50) NOT NULL,
            `phone` VARCHAR(20) NOT NULL,
            `id_card` VARCHAR(50) PRIMARY KEY
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS `Salespersons` (
            `salesperson_id` VARCHAR(10) PRIMARY KEY,
            `salesperson_name` VARCHAR(50) NOT NULL,
            `contact_number` VARCHAR(20) NOT NULL,
            `email` VARCHAR(100) NOT NULL UNIQUE,
            `password` VARCHAR(255) NOT NULL,
            `role` ENUM('Manager', 'Salesperson') NOT NULL
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS `SalesOrders` (
            `order_id` VARCHAR(20) PRIMARY KEY,
            `train_number` VARCHAR(10) NOT NULL,
            `train_type` VARCHAR(20) NOT NULL,
            `start_date` DATE NOT NULL,
            `departure_station` VARCHAR(20) NOT NULL,
            `arrival_station` VARCHAR(20) NOT NULL,
            `price` DECIMAL(10, 2) NOT NULL,
            `customer_name` VARCHAR(20) NOT NULL,
            `customer_phone` VARCHAR(20) NOT NULL,
            `operation_type` ENUM('Booking', 'Refund') NOT NULL,
            `operation_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            `status` ENUM('Ready', 'Success', 'Cancelled', 'RefundPending', 'Refunded') NOT NULL DEFAULT 'Ready'
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS `OrderOperations` (
            `operation_id` INT PRIMARY KEY AUTO_INCREMENT,
            `order_id` VARCHAR(20) NOT NULL,
            `salesperson_id` VARCHAR(10) NOT NULL,
            `operation_type` ENUM('Approve', 'Reject') NOT NULL,
            `original_status` ENUM('Ready', 'RefundPending') NOT NULL,
            `new_status` ENUM('Success', 'Cancelled', 'Refunded') NOT NULL,
            `price` INT NOT NULL,
            `operation_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            `remarks` VARCHAR(255),
            FOREIGN KEY (`order_id`) REFERENCES `SalesOrders`(`order_id`),
            FOREIGN KEY (`salesperson_id`) REFERENCES `Salespersons`(`salesperson_id`)
        );
        """
    ]
    
    for stmt in table_statements:
        try:
            cursor.execute(stmt)
            print(f"Created table: {stmt.split('CREATE TABLE IF NOT EXISTS')[1].split('(')[0].strip()}")
        except Error as err:
            print(f"Error creating table: {err}")
            raise

def create_views(cursor):
    """Create all views"""
    view_statements = [
        """
        DROP VIEW IF EXISTS `TrainSchedulesView`
        """,
        """
        CREATE VIEW `TrainSchedulesView` AS
        SELECT
            T.train_number,
            DS.station_name AS departure_station,
            AS_st.station_name AS arrival_station,
            T.train_type,
            SS.station_name AS stopover_station,
            S.stop_order,
            S.seats,
            S.arrival_time,
            S.departure_time
        FROM
            `Trains` T
        JOIN
            `Stations` DS ON T.departure_station_id = DS.station_id
        JOIN
            `Stations` AS_st ON T.arrival_station_id = AS_st.station_id
        LEFT JOIN
            `Stopovers` S ON T.train_number = S.train_number
        LEFT JOIN
            `Stations` SS ON S.station_id = SS.station_id
        ORDER BY
            T.train_number, S.Start_date, S.stop_order
        """,
        """
        DROP VIEW IF EXISTS `PendingOrdersView`
        """,
        """
        CREATE VIEW `PendingOrdersView` AS
        SELECT 
            order_id,
            train_number,
            train_type,
            departure_station,
            arrival_station,
            price,
            customer_name,
            customer_phone,
            operation_type,
            operation_time,
            status
        FROM 
            `SalesOrders`
        WHERE 
            status IN ('Ready', 'RefundPending')
        ORDER BY 
            operation_time DESC
        """,
        """
        DROP VIEW IF EXISTS `OrderOperationsView`
        """,
        """
        CREATE VIEW `OrderOperationsView` AS
        SELECT 
            op.operation_id,
            op.order_id,
            so.train_number,
            so.customer_name,
            sp.salesperson_name,
            op.operation_type,
            op.original_status,
            op.new_status,
            op.price,
            op.operation_time,
            op.remarks
        FROM 
            `OrderOperations` op
        JOIN 
            `SalesOrders` so ON op.order_id = so.order_id
        JOIN 
            `Salespersons` sp ON op.salesperson_id = sp.salesperson_id
        ORDER BY 
            op.operation_time DESC
        """
    ]
    
    for stmt in view_statements:
        try:
            cursor.execute(stmt)
            print(f"Created view: {stmt.split('CREATE VIEW')[1].split('AS')[0].strip() if 'CREATE VIEW' in stmt else 'Dropped view'}")
        except Error as err:
            print(f"Error creating view: {err}")
            raise

def create_indexes(cursor):
    """Create all indexes"""
    index_statements = [
        "CREATE INDEX idx_trains_departure_station_id ON `Trains` (`departure_station_id`)",
        "CREATE INDEX idx_trains_arrival_station_id ON `Trains` (`arrival_station_id`)",
        "CREATE INDEX idx_stopovers_station_id ON `Stopovers` (`station_id`)",
        "CREATE INDEX idx_prices_departure_station_id ON `Prices` (`departure_station_id`)",
        "CREATE INDEX idx_prices_arrival_station_id ON `Prices` (`arrival_station_id`)",
        "CREATE INDEX idx_customers_id_card ON `Customers` (`id_card`)",
        "CREATE INDEX idx_salespersons_id ON `Salespersons` (`salesperson_id`)",
        "CREATE INDEX idx_orders_train_number ON `SalesOrders` (`train_number`)",
        "CREATE INDEX idx_orders_operation_time ON `SalesOrders` (`operation_time`)",
        "CREATE INDEX idx_order_operations_time ON `OrderOperations` (`operation_time`)"
    ]
    
    for stmt in index_statements:
        try:
            cursor.execute(stmt)
            print(f"Created index: {stmt.split('CREATE INDEX')[1].split('ON')[0].strip()}")
        except Error as err:
            if err.errno != 1061:  # 1061 is MySQL error code for duplicate key name
                print(f"Error creating index: {err}")
                raise

def create_triggers(cursor):
    """Create all triggers"""
    trigger_statements = [
        """
        DROP TRIGGER IF EXISTS after_order_success;
        """,
        """
        CREATE TRIGGER after_order_success
        AFTER UPDATE ON `SalesOrders`
        FOR EACH ROW
        BEGIN
            DECLARE dep_order INT;
            DECLARE arr_order INT;
            
            -- Get departure and arrival stop orders first
            SELECT stop_order INTO dep_order
            FROM Stopovers s2 
            JOIN Stations st2 ON st2.station_id = s2.station_id 
            WHERE s2.train_number = NEW.train_number 
            AND s2.start_date = NEW.start_date
            AND st2.station_name = NEW.departure_station;
            
            SELECT stop_order INTO arr_order
            FROM Stopovers s3 
            JOIN Stations st3 ON st3.station_id = s3.station_id 
            WHERE s3.train_number = NEW.train_number 
            AND s3.start_date = NEW.start_date
            AND st3.station_name = NEW.arrival_station;
            
            IF NEW.status = 'Success' AND OLD.status = 'Ready' THEN
                UPDATE Stopovers s
                JOIN Stations st ON st.station_id = s.station_id
                SET s.seats = s.seats - 1
                WHERE s.train_number = NEW.train_number
                AND s.start_date = NEW.start_date
                AND s.seats > 0
                AND s.stop_order >= dep_order
                AND s.stop_order < arr_order;
            END IF;
        END;
        """,
        """
        DROP TRIGGER IF EXISTS after_order_refund;
        """,
        """
        CREATE TRIGGER after_order_refund
        AFTER UPDATE ON `SalesOrders`
        FOR EACH ROW
        BEGIN
            DECLARE dep_order INT;
            DECLARE arr_order INT;
            
            -- Get departure and arrival stop orders first
            SELECT stop_order INTO dep_order
            FROM Stopovers s2 
            JOIN Stations st2 ON st2.station_id = s2.station_id 
            WHERE s2.train_number = NEW.train_number 
            AND s2.start_date = NEW.start_date
            AND st2.station_name = NEW.departure_station;
            
            SELECT stop_order INTO arr_order
            FROM Stopovers s3 
            JOIN Stations st3 ON st3.station_id = s3.station_id 
            WHERE s3.train_number = NEW.train_number 
            AND s3.start_date = NEW.start_date
            AND st3.station_name = NEW.arrival_station;
            
            IF NEW.status = 'Refunded' AND OLD.status = 'RefundPending' THEN
                UPDATE Stopovers s
                JOIN Stations st ON st.station_id = s.station_id
                SET s.seats = s.seats + 1
                WHERE s.train_number = NEW.train_number
                AND s.start_date = NEW.start_date
                AND s.stop_order >= dep_order
                AND s.stop_order < arr_order;
            END IF;
        END;
        """
    ]
    
    for stmt in trigger_statements:
        try:
            cursor.execute(stmt)
            if "CREATE TRIGGER" in stmt:
                print(f"Created trigger: {stmt.split('CREATE TRIGGER')[1].split('\n')[0].strip()}")
            else:
                print(f"Dropped trigger: {stmt.split('DROP TRIGGER IF EXISTS')[1].split(';')[0].strip()}")
        except Error as err:
            print(f"Error creating trigger: {err}")
            raise

def create_procedures(cursor):
    """Create all stored procedures"""
    procedure_statements = [
        """
        DROP PROCEDURE IF EXISTS sp_daily_sales_report;
        """,
        """
        CREATE PROCEDURE sp_daily_sales_report(IN report_date DATE)
        BEGIN
            SELECT 
                s.salesperson_id,
                s.salesperson_name,
                COUNT(DISTINCT o.order_id) as total_orders,
                SUM(CASE 
                    WHEN o.operation_type = 'Booking' AND o.status = 'Success' 
                    THEN op.price 
                    ELSE 0 
                END) as booking_revenue,
                SUM(CASE 
                    WHEN o.operation_type = 'Refund' AND o.status = 'Refunded' 
                    THEN op.price 
                    ELSE 0 
                END) as refund_amount
            FROM 
                Salespersons s
                LEFT JOIN OrderOperations op ON s.salesperson_id = op.salesperson_id
                LEFT JOIN SalesOrders o ON op.order_id = o.order_id
            WHERE 
                DATE(op.operation_time) = report_date
                AND op.operation_type = 'Approve'
                AND o.status IN ('Success', 'Refunded')
            GROUP BY 
                s.salesperson_id, s.salesperson_name
            ORDER BY 
                (booking_revenue + refund_amount) DESC;
        END;
        """,
        """
        DROP PROCEDURE IF EXISTS sp_daily_staff_report;
        """,
        """
        CREATE PROCEDURE sp_daily_staff_report(
            IN report_date DATE,
            IN staff_id VARCHAR(10)
        )
        BEGIN
            SELECT 
                s.salesperson_id,
                s.salesperson_name,
                COUNT(DISTINCT o.order_id) as total_orders,
                SUM(CASE 
                    WHEN o.operation_type = 'Booking' AND o.status = 'Success' 
                    THEN op.price 
                    ELSE 0 
                END) as booking_revenue,
                SUM(CASE 
                    WHEN o.operation_type = 'Refund' AND o.status = 'Refunded' 
                    THEN op.price 
                    ELSE 0 
                END) as refund_amount
            FROM 
                Salespersons s
                LEFT JOIN OrderOperations op ON s.salesperson_id = op.salesperson_id
                LEFT JOIN SalesOrders o ON op.order_id = o.order_id
            WHERE 
                DATE(op.operation_time) = report_date
                AND op.operation_type = 'Approve'
                AND o.status IN ('Success', 'Refunded')
                AND s.salesperson_id = staff_id
            GROUP BY 
                s.salesperson_id, s.salesperson_name;
        END;
        """,
        """
        DROP PROCEDURE IF EXISTS sp_get_train_route;
        """,
        """
        CREATE PROCEDURE sp_get_train_route(
            IN p_train_number VARCHAR(10),
            IN p_departure_date DATE
        )
        BEGIN
            DECLARE v_departure_station_id INT;
            DECLARE v_arrival_station_id INT;
            DECLARE v_total_seats INT;
            
            -- Get train's departure and arrival stations and total seats
            SELECT departure_station_id, arrival_station_id, total_seats
            INTO v_departure_station_id, v_arrival_station_id, v_total_seats
            FROM Trains 
            WHERE train_number = p_train_number;
            
            IF p_departure_date IS NOT NULL THEN
                SELECT 
                    s.train_number,
                    s.start_date,
                    st.station_name,
                    st.station_code,
                    s.arrival_time,
                    s.departure_time,
                    CASE 
                        WHEN st.station_id = v_departure_station_id THEN 'Departure'
                        WHEN st.station_id = v_arrival_station_id THEN 'Arrival'
                        ELSE 'Stopover'
                    END as stop_type,
                    s.stop_order,
                    (v_total_seats - s.seats) as sold_tickets
                FROM 
                    Stopovers s
                JOIN 
                    Stations st ON s.station_id = st.station_id
                WHERE 
                    s.train_number = p_train_number
                    AND s.start_date = p_departure_date
                ORDER BY 
                    s.stop_order;
            ELSE
                SELECT 
                    s.train_number,
                    s.start_date,
                    st.station_name,
                    st.station_code,
                    s.arrival_time,
                    s.departure_time,
                    CASE 
                        WHEN st.station_id = v_departure_station_id THEN 'Departure'
                        WHEN st.station_id = v_arrival_station_id THEN 'Arrival'
                        ELSE 'Stopover'
                    END as stop_type,
                    s.stop_order,
                    (v_total_seats - s.seats) as sold_tickets
                FROM 
                    Stopovers s
                JOIN 
                    Stations st ON s.station_id = st.station_id
                WHERE 
                    s.train_number = p_train_number
                ORDER BY 
                    s.start_date, s.stop_order;
            END IF;
        END;
        """
    ]
    
    for stmt in procedure_statements:
        try:
            cursor.execute(stmt)
            if "CREATE PROCEDURE" in stmt:
                print(f"Created procedure: {stmt.split('CREATE PROCEDURE')[1].split('(')[0].strip()}")
            else:
                print(f"Dropped procedure: {stmt.split('DROP PROCEDURE IF EXISTS')[1].split(';')[0].strip()}")
        except Error as err:
            print(f"Error creating procedure: {err}")
            raise

if __name__ == "__main__":
    print("Setting up database...")
    if setup_database(drop_existing=True):
        print("Database setup successful!")
    else:
        print("Database setup failed.")