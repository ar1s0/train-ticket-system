import mysql.connector
from mysql.connector import Error
from db_config import DB_CONFIG
import random
from datetime import datetime, timedelta
import csv
import json
import os

def insert_sample_data():
    """
    Inserts sample data into the database for testing and demonstration purposes
    """
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(buffered=True)
        
        # Clear existing data (optional)
        clear_existing_data(cursor)
        
        # Insert sample data in correct dependency order
        station_ids = insert_stations_from_csv(cursor)
        train_numbers = insert_trains_from_csv(cursor, station_ids)
        insert_stopovers_from_csv(cursor, train_numbers, station_ids)
        price_data = insert_prices_from_config(cursor, train_numbers)
        insert_customers_from_csv(cursor)
        insert_salespersons_from_csv(cursor)  # Add this line
        insert_sample_orders(cursor)
        
        conn.commit()
        print("Sample data inserted successfully!")
        return True
        
    except Error as e:
        conn.rollback()
        print(f"Error inserting sample data: {e}")
        return False
        
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

def clear_existing_data(cursor):
    """Clear existing data from all tables"""
    # Disable foreign key checks temporarily
    cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
    
    tables = [
        "SalesOrders",
        "Salespersons", "Prices", "Stopovers", 
        "Trains", "Stations", "Customers"  # Added Customers table
    ]
    
    for table in tables:
        try:
            cursor.execute(f"TRUNCATE TABLE `{table}`")
            print(f"Cleared data from {table}")
        except Error as e:
            print(f"Error clearing {table}: {e}")
    
    # Re-enable foreign key checks
    cursor.execute("SET FOREIGN_KEY_CHECKS = 1")

def read_csv_file(filename):
    """Helper function to read CSV files from resources directory"""
    filepath = os.path.join('resources', filename)
    with open(filepath, mode='r', encoding='utf-8') as file:
        return list(csv.DictReader(file))

def insert_stations_from_csv(cursor):
    """Insert stations from CSV file and return station_id mapping"""
    stations_data = read_csv_file('stations.csv')
    
    station_ids = {}
    for row in stations_data:
        cursor.execute(
            "INSERT INTO `Stations` (`station_name`, `station_code`) VALUES (%s, %s)",
            (row['station_name'], row['station_code'])
        )
        station_id = cursor.lastrowid
        station_ids[row['station_name']] = station_id
    
    print(f"Inserted {len(stations_data)} stations")
    return station_ids

def insert_trains_from_csv(cursor, station_ids):
    """Insert trains from CSV file and return train numbers"""
    trains_data = read_csv_file('trains.csv')
    
    train_seats = {}
    for row in trains_data:
        dep_id = station_ids[row['departure_station']]
        arr_id = station_ids[row['arrival_station']]
        
        cursor.execute(
            "INSERT INTO `Trains` (`train_number`, `train_type`, `total_seats`, `departure_station_id`, `arrival_station_id`) VALUES (%s, %s, %s, %s, %s)",
            (row['train_number'], row['train_type'], int(row['total_seats']), dep_id, arr_id)
        )
        train_seats[row['train_number']] = row['total_seats']
    
    print(f"Inserted {len(trains_data)} trains")
    return train_seats

def insert_stopovers_from_csv(cursor, train_seats, station_ids):
    """Insert stopovers from CSV file"""
    stopovers_data = read_csv_file('stopovers.csv')
    
    inserted_count = 0
    for row in stopovers_data:
        if row['train_number'] not in train_seats:
            continue
            
        station_id = station_ids.get(row['station_name'])
        if not station_id:
            continue

        arrival_time = None
        if row['arrival_time'] != "-":
            arrival_time = datetime.strptime(row['arrival_time'], '%Y-%m-%d %H:%M:%S')

        departure_time = None 
        if row['departure_time'] != "-":
            departure_time = datetime.strptime(row['departure_time'], '%Y-%m-%d %H:%M:%S')

        cursor.execute(
            "INSERT INTO `Stopovers` (`train_number`, `station_id`, `arrival_time`, `departure_time`, `stop_order`, `seats`) VALUES (%s, %s, %s, %s, %s, %s)",
            (row['train_number'], station_id, arrival_time, departure_time, int(row['stop_order']), train_seats[row['train_number']])
        )
        inserted_count += 1
    
    print(f"Inserted {inserted_count} stopovers")

def insert_prices_from_config(cursor, train_numbers):
    """
    Insert prices based on train type configuration
    Ensures prices are only created for valid train routes
    """
    seat_types_data = read_csv_file('seat_types.csv')
    
    price_data = []
    
    # Get all valid train routes
    cursor.execute(
        "SELECT train_number, departure_station_id, arrival_station_id, train_type FROM Trains"
    )
    valid_trains = {(train[0], train[1], train[2], train[3]) 
                   for train in cursor.fetchall() 
                   if train[0] in train_numbers}
    
    for row in seat_types_data:
        # Only process prices for trains of matching type
        matching_trains = [train for train in valid_trains 
                         if train[3] == row['train_type']]
        
        for train_num, dep_id, arr_id, _ in matching_trains:
            # Add some random variation to base price
            base_price = float(row['base_price'])
            price = round(base_price * random.uniform(0.9, 1.1), 2)
            
            cursor.execute(
                """INSERT INTO `Prices` 
                   (`train_number`, `departure_station_id`, `arrival_station_id`, 
                    `price`) 
                   VALUES (%s, %s, %s, %s)""",
                (train_num, dep_id, arr_id, price)
            )
            
            price_data.append({
                "train_number": train_num,
                "departure_station_id": dep_id,
                "arrival_station_id": arr_id,
                "price": price
            })
    
    print(f"Inserted {len(price_data)} prices")
    return price_data

def insert_customers_from_csv(cursor):
    """Insert customers from CSV file"""
    customers_data = read_csv_file('customer.csv')
    
    inserted_count = 0
    for row in customers_data:
        try:
            cursor.execute(
                "INSERT INTO `Customers` (`name`, `phone`, `id_card`) VALUES (%s, %s, %s)",
                (row['name'], row['phone'], row['id_card'])
            )
            inserted_count += 1
        except Error as e:
            print(f"Error inserting customer {row['name']}: {e}")
            continue
    
    print(f"Inserted {inserted_count} customers")
    return inserted_count

def insert_salespersons_from_csv(cursor):
    """Insert salespersons from CSV file"""
    salespersons_data = read_csv_file('salespersons.csv')
    
    inserted_count = 0
    for row in salespersons_data:
        try:
            cursor.execute(
                """INSERT INTO `Salespersons` 
                   (`salesperson_id`, `salesperson_name`, `contact_number`, 
                    `email`, `password`, `role`) 
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (row['salesperson_id'], row['salesperson_name'], 
                 row['contact_number'], row['email'], 
                 row['password'], row['role'])
            )
            inserted_count += 1
        except Error as e:
            print(f"Error inserting salesperson {row['salesperson_name']}: {e}")
            continue
    
    print(f"Inserted {inserted_count} salespersons")
    return inserted_count

def insert_sample_orders(cursor):
    """Insert sample orders into the SalesOrders table"""
    print("Inserting sample orders...")
    
    # 获取所有客户信息
    cursor.execute("SELECT name, phone FROM Customers")
    customers = cursor.fetchall()
    
    # 获取所有列车信息
    cursor.execute("""
        SELECT t.train_number, t.train_type, 
               dep.station_name as departure_station, 
               arr.station_name as arrival_station
        FROM Trains t
        JOIN Stations dep ON t.departure_station_id = dep.station_id
        JOIN Stations arr ON t.arrival_station_id = arr.station_id
    """)
    trains = cursor.fetchall()
    
    if not customers or not trains:
        print("No customers or trains found for generating orders")
        return 0
    
    # 生成示例订单
    from datetime import datetime, timedelta
    import random
    
    orders_data = []
    base_time = datetime.now() - timedelta(days=30)  # 从30天前开始
    
    for i in range(10):  # 生成50个订单
        customer = random.choice(customers)
        train = random.choice(trains)
        
        # 生成订单号 (年月日时分秒+4位随机数)
        order_time = base_time + timedelta(
            days=random.randint(0, 29),
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59)
        )
        order_id = order_time.strftime('%Y%m%d%H%M%S') + str(random.randint(1000, 9999))
        
        # 随机生成价格 (200-1000之间)
        price = round(random.uniform(200, 1000), 2)
        
        # 随机生成订单状态
        status = random.choice(['Ready', 'Success', 'Cancelled', 'RefundPending', 'Refunded'])
        operation_type = 'Refund' if status in ('Refunded', 'RefundPending') else 'Booking'
        
        orders_data.append((
            order_id,
            train[0],  # train_number
            train[1],  # train_type
            train[2],  # departure_station
            train[3],  # arrival_station
            price,
            customer[0],  # customer_name
            customer[1],  # customer_phone
            operation_type,
            order_time,
            status
        ))
    
    # 批量插入订单
    try:
        cursor.executemany("""
            INSERT INTO SalesOrders (
                order_id, train_number, train_type,
                departure_station, arrival_station,
                price, customer_name, customer_phone,
                operation_type, operation_time, status
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, orders_data)
        
        print(f"Successfully inserted {len(orders_data)} sample orders")
        return len(orders_data)
        
    except Error as e:
        print(f"Error inserting sample orders: {e}")
        return 0

# 修改 insert_sample_data 函数，在末尾添加对新函数的调用
def insert_sample_data():
    """Inserts sample data into the database"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(buffered=True)
        
        # Clear existing data (optional)
        clear_existing_data(cursor)
        
        # Insert sample data in correct dependency order
        station_ids = insert_stations_from_csv(cursor)
        train_numbers = insert_trains_from_csv(cursor, station_ids)
        insert_stopovers_from_csv(cursor, train_numbers, station_ids)
        price_data = insert_prices_from_config(cursor, train_numbers)
        insert_customers_from_csv(cursor)
        insert_salespersons_from_csv(cursor)  # Add this line
        insert_sample_orders(cursor)
        
        conn.commit()
        print("Sample data inserted successfully!")
        return True
        
    except Error as e:
        conn.rollback()
        print(f"Error inserting sample data: {e}")
        return False
        
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

if __name__ == "__main__":
    print("=== Inserting sample data ===")
    if insert_sample_data():
        print("Sample data insertion successful!")
    else:
        print("Sample data insertion failed.")