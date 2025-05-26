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
            `arrival_time` DATETIME NULL,
            `departure_time` DATETIME NULL,
            `stop_order` INT NOT NULL CHECK (`stop_order` > 0),
            `seats` INT NOT NULL CHECK (`seats` >= 0),
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
            `price` DECIMAL(10, 2) NOT NULL CHECK (`price` >= 0),
            FOREIGN KEY (`train_number`) REFERENCES `Trains`(`train_number`),
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
            `role` ENUM('Admin', 'Salesperson') NOT NULL
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
            T.train_number, S.stop_order
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
        "CREATE INDEX idx_salespersons_id ON `Salespersons` (`salesperson_id`)"
    ]
    
    for stmt in index_statements:
        try:
            cursor.execute(stmt)
            print(f"Created index: {stmt.split('CREATE INDEX')[1].split('ON')[0].strip()}")
        except Error as err:
            if err.errno != 1061:  # 1061 is MySQL error code for duplicate key name
                print(f"Error creating index: {err}")
                raise

if __name__ == "__main__":
    print("Setting up database...")
    if setup_database(drop_existing=True):
        print("Database setup successful!")
    else:
        print("Database setup failed.")