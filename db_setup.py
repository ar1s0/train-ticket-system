# db_setup.py

import mysql.connector
from mysql.connector import Error
from db_config import DB_CONFIG
from db_sample_data import insert_sample_data

def setup_database(drop_existing=False):
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
            # Triggers
            create_triggers(cursor)
            # Procedures
            create_procedures(cursor)
            # Views
            create_views(cursor)
            # Indexes
            create_indexes(cursor)


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
            `total_seats` INT NOT NULL CHECK (`total_seats` > 0),
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
            `arrival_time` TIME NULL,
            `departure_time` TIME NULL,
            `stop_order` INT NOT NULL CHECK (`stop_order` > 0),
            FOREIGN KEY (`train_number`) REFERENCES `Trains`(`train_number`),
            FOREIGN KEY (`station_id`) REFERENCES `Stations`(`station_id`),
            UNIQUE (`train_number`, `station_id`),
            UNIQUE (`train_number`, `stop_order`)
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS `Prices` (
            `price_id` INT PRIMARY KEY AUTO_INCREMENT,
            `train_number` VARCHAR(10) NOT NULL,
            `departure_station_id` INT NOT NULL,
            `arrival_station_id` INT NOT NULL,
            `seat_type` ENUM('Hard Seat', 'Soft Seat', 'Hard Sleeper', 'Soft Sleeper', 'Business Class', 'First Class', 'Second Class') NOT NULL,
            `price` DECIMAL(10, 2) NOT NULL CHECK (`price` >= 0),
            FOREIGN KEY (`train_number`) REFERENCES `Trains`(`train_number`),
            FOREIGN KEY (`departure_station_id`) REFERENCES `Stations`(`station_id`),
            FOREIGN KEY (`arrival_station_id`) REFERENCES `Stations`(`station_id`),
            UNIQUE (`train_number`, `departure_station_id`, `arrival_station_id`, `seat_type`)
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS `Salespersons` (
            `salesperson_id` VARCHAR(20) PRIMARY KEY,
            `salesperson_name` VARCHAR(50) NOT NULL,
            `contact_number` VARCHAR(20) UNIQUE NULL,
            `email` VARCHAR(100) UNIQUE NULL,
            `password_hash` VARCHAR(255) NOT NULL,
            `role` ENUM('Salesperson', 'Admin') NOT NULL DEFAULT 'Salesperson'
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS `DailyTrainStatus` (
            `train_number` VARCHAR(10) NOT NULL,
            `departure_date` DATE NOT NULL,
            `remaining_seats` INT NOT NULL,
            PRIMARY KEY (`train_number`, `departure_date`),
            FOREIGN KEY (`train_number`) REFERENCES `Trains`(`train_number`)
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS `SalesOrders` (
            `order_id` VARCHAR(30) PRIMARY KEY,
            `train_number` VARCHAR(10) NOT NULL,
            `departure_date` DATE NOT NULL,
            `seat_number` VARCHAR(10) NOT NULL,
            `passenger_name` VARCHAR(50) NOT NULL,
            `id_type` VARCHAR(20) NOT NULL,
            `id_number` VARCHAR(30) NOT NULL,
            `departure_station_id` INT NOT NULL,
            `arrival_station_id` INT NOT NULL,
            `ticket_price` DECIMAL(10, 2) NOT NULL CHECK (`ticket_price` >= 0),
            `sales_time` DATETIME DEFAULT CURRENT_TIMESTAMP,
            `salesperson_id` VARCHAR(20) NOT NULL,
            `order_status` ENUM('Sold', 'Refunded', 'Canceled') NOT NULL DEFAULT 'Sold',
            FOREIGN KEY (`train_number`) REFERENCES `Trains`(`train_number`),
            FOREIGN KEY (`departure_station_id`) REFERENCES `Stations`(`station_id`),
            FOREIGN KEY (`arrival_station_id`) REFERENCES `Stations`(`station_id`),
            FOREIGN KEY (`salesperson_id`) REFERENCES `Salespersons`(`salesperson_id`),
            UNIQUE (`train_number`, `departure_date`, `seat_number`)
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS `Refunds` (
            `refund_id` VARCHAR(30) PRIMARY KEY,
            `order_id` VARCHAR(30) NOT NULL,
            `refund_time` DATETIME DEFAULT CURRENT_TIMESTAMP,
            `refund_amount` DECIMAL(10, 2) NOT NULL CHECK (`refund_amount` >= 0),
            `salesperson_id` VARCHAR(20) NOT NULL,
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

def create_triggers(cursor):
    """Create all triggers"""
    trigger_statements = [
        """
        DROP TRIGGER IF EXISTS `After_SalesOrder_Insert`
        """,
        """
        CREATE TRIGGER `After_SalesOrder_Insert`
        AFTER INSERT ON `SalesOrders`
        FOR EACH ROW
        BEGIN
            INSERT INTO `DailyTrainStatus` (`train_number`, `departure_date`, `remaining_seats`)
            VALUES (NEW.train_number, NEW.departure_date, 
                   (SELECT `total_seats` FROM `Trains` WHERE `train_number` = NEW.train_number) - 1)
            ON DUPLICATE KEY UPDATE `remaining_seats` = `remaining_seats` - 1;
        END;
        """,
        """
        DROP TRIGGER IF EXISTS `Before_SalesOrder_Insert`
        """,
        """
        CREATE TRIGGER `Before_SalesOrder_Insert`
        BEFORE INSERT ON `SalesOrders`
        FOR EACH ROW
        BEGIN
            DECLARE v_remaining_seats INT;
            SELECT `remaining_seats`
            INTO v_remaining_seats
            FROM `DailyTrainStatus`
            WHERE `train_number` = NEW.train_number AND `departure_date` = NEW.departure_date;

            IF v_remaining_seats IS NULL THEN
                SELECT `total_seats` INTO v_remaining_seats FROM `Trains` WHERE `train_number` = NEW.train_number;
            END IF;

            IF v_remaining_seats <= 0 THEN
                SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Error: Cannot sell ticket. No remaining seats for this train and date.';
            END IF;
        END;
        """,
        """
        DROP TRIGGER IF EXISTS `After_Refund_Insert`
        """,
        """
        CREATE TRIGGER `After_Refund_Insert`
        AFTER INSERT ON `Refunds`
        FOR EACH ROW
        BEGIN
            DECLARE sold_train_number VARCHAR(10);
            DECLARE sold_departure_date DATE;

            SELECT `train_number`, `departure_date`
            INTO sold_train_number, sold_departure_date
            FROM `SalesOrders`
            WHERE `order_id` = NEW.order_id;

            UPDATE `DailyTrainStatus`
            SET `remaining_seats` = `remaining_seats` + 1
            WHERE `train_number` = sold_train_number AND `departure_date` = sold_departure_date;

            UPDATE `SalesOrders`
            SET `order_status` = 'Refunded'
            WHERE `order_id` = NEW.order_id;
        END;
        """
    ]
    
    for stmt in trigger_statements:
        try:
            cursor.execute(stmt)
            print(f"Created trigger: {stmt.split('CREATE TRIGGER')[1].split('AFTER')[0].strip() if 'CREATE TRIGGER' in stmt else 'Dropped trigger'}")
        except Error as err:
            print(f"Error creating trigger: {err}")
            raise

def create_procedures(cursor):
    """Create all stored procedures"""
    procedure_statements = [
        """
        DROP PROCEDURE IF EXISTS `GetTrainSalesSummary`
        """,
        """
        CREATE PROCEDURE `GetTrainSalesSummary`(IN p_train_number VARCHAR(10), IN p_departure_date DATE)
        BEGIN
            SELECT
                SO.train_number,
                SO.departure_date,
                COUNT(SO.order_id) AS total_tickets_sold,
                SUM(SO.ticket_price) AS total_sales_amount
            FROM
                `SalesOrders` SO
            WHERE
                SO.train_number = p_train_number
                AND SO.departure_date = p_departure_date
                AND SO.order_status = 'Sold'
            GROUP BY
                SO.train_number, SO.departure_date;
        END;
        """,
        """
        DROP PROCEDURE IF EXISTS `GetSalespersonDailyRevenue`
        """,
        """
        CREATE PROCEDURE `GetSalespersonDailyRevenue`(IN p_sales_date DATE)
        BEGIN
            SELECT
                S.salesperson_id,
                S.salesperson_name,
                SUM(SO.ticket_price) AS total_revenue
            FROM
                `SalesOrders` SO
            JOIN
                `Salespersons` S ON SO.salesperson_id = S.salesperson_id
            WHERE
                DATE(SO.sales_time) = p_sales_date
                AND SO.order_status = 'Sold'
            GROUP BY
                S.salesperson_id, S.salesperson_name
            ORDER BY
                total_revenue DESC;
        END;
        """
    ]
    
    for stmt in procedure_statements:
        try:
            cursor.execute(stmt)
            print(f"Created procedure: {stmt.split('CREATE PROCEDURE')[1].split('(')[0].strip() if 'CREATE PROCEDURE' in stmt else 'Dropped procedure'}")
        except Error as err:
            print(f"Error creating procedure: {err}")
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
            T.train_type,
            DS.station_name AS departure_station,
            AS_st.station_name AS arrival_station,
            S.stop_order,
            SS.station_name AS stopover_station,
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
            T.train_number, S.stop_order
        """,
        """
        DROP VIEW IF EXISTS `AvailableTicketsView`
        """,
        """
        CREATE VIEW `AvailableTicketsView` AS
        SELECT
            DTS.train_number,
            DTS.departure_date,
            DTS.remaining_seats,
            DS.station_name AS departure_station_name,
            AS_st.station_name AS arrival_station_name,
            P.seat_type,
            P.price
        FROM
            `DailyTrainStatus` DTS
        JOIN
            `Trains` T ON DTS.train_number = T.train_number
        JOIN
            `Stations` DS ON T.departure_station_id = DS.station_id
        JOIN
            `Stations` AS_st ON T.arrival_station_id = AS_st.station_id
        JOIN
            `Prices` P ON T.train_number = P.train_number AND P.departure_station_id = DS.station_id AND P.arrival_station_id = AS_st.station_id
        WHERE
            DTS.remaining_seats > 0
        """,
        """
        DROP VIEW IF EXISTS `SalespersonSalesSummaryView`
        """,
        """
        CREATE VIEW `SalespersonSalesSummaryView` AS
        SELECT
            S.salesperson_id,
            S.salesperson_name,
            COUNT(SO.order_id) AS total_tickets_sold,
            SUM(SO.ticket_price) AS total_sales_value
        FROM
            `Salespersons` S
        LEFT JOIN
            `SalesOrders` SO ON S.salesperson_id = SO.salesperson_id AND SO.order_status = 'Sold'
        GROUP BY
            S.salesperson_id, S.salesperson_name
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
        "CREATE INDEX idx_salesorders_salesperson_id ON `SalesOrders` (`salesperson_id`)",
        "CREATE INDEX idx_salesorders_departure_date ON `SalesOrders` (`departure_date`)",
        "CREATE INDEX idx_salesorders_train_departure_date_status ON `SalesOrders` (`train_number`, `departure_date`, `order_status`)",
        "CREATE INDEX idx_refunds_order_id ON `Refunds` (`order_id`)",
        "CREATE INDEX idx_dailytrainstatus_remaining_seats ON `DailyTrainStatus` (`remaining_seats`)"
    ]
    
    for stmt in index_statements:
        try:
            cursor.execute(stmt)
            print(f"Created index: {stmt.split('CREATE INDEX')[1].split('ON')[0].strip()}")
        except Error as err:
            # Ignore if index already exists
            if err.errno != 1061:  # 1061 is MySQL error code for duplicate key name
                print(f"Error creating index: {err}")
                raise

if __name__ == "__main__":
    print("Setting up database...")
    if setup_database(drop_existing=True):
        print("Database setup successful!")
    else:
        print("Database setup failed.")