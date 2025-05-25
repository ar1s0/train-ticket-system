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
        price_data = insert_prices_from_config(cursor, train_numbers, station_ids)
        salesperson_ids = insert_salespersons_from_csv(cursor)
        daily_status = insert_daily_train_status(cursor, train_numbers)
        
        # Insert sales orders with guaranteed valid data
        insert_sample_orders(cursor, train_numbers, station_ids, salesperson_ids, price_data)
        
        # Insert refunds for some orders
        insert_refunds(cursor, salesperson_ids)
        
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
        "Refunds", "SalesOrders", "DailyTrainStatus", 
        "Salespersons", "Prices", "Stopovers", 
        "Trains", "Stations"
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
    
    train_numbers = []
    for row in trains_data:
        dep_id = station_ids[row['departure_station']]
        arr_id = station_ids[row['arrival_station']]
        
        cursor.execute(
            "INSERT INTO `Trains` (`train_number`, `train_type`, `total_seats`, `departure_station_id`, `arrival_station_id`) VALUES (%s, %s, %s, %s, %s)",
            (row['train_number'], row['train_type'], int(row['total_seats']), dep_id, arr_id)
        )
        train_numbers.append(row['train_number'])
    
    print(f"Inserted {len(trains_data)} trains")
    return train_numbers

def insert_stopovers_from_csv(cursor, train_numbers, station_ids):
    """Insert stopovers from CSV file"""
    stopovers_data = read_csv_file('stopovers.csv')
    
    inserted_count = 0
    for row in stopovers_data:
        if row['train_number'] not in train_numbers:
            continue
            
        station_id = station_ids.get(row['station_name'])
        if not station_id:
            continue
        
        # 处理时间字段，如果是"-"则设为None
        arrival_time = None if row['arrival_time'] == "-" else row['arrival_time']
        departure_time = None if row['departure_time'] == "-" else row['departure_time']
            
        cursor.execute(
            "INSERT INTO `Stopovers` (`train_number`, `station_id`, `arrival_time`, `departure_time`, `stop_order`) VALUES (%s, %s, %s, %s, %s)",
            (row['train_number'], station_id, arrival_time, departure_time, int(row['stop_order']))
        )
        inserted_count += 1
    
    print(f"Inserted {inserted_count} stopovers")

def insert_prices_from_config(cursor, train_numbers, station_ids):
    """Insert prices based on seat type configuration"""
    seat_types_data = read_csv_file('seat_types.csv')
    
    price_data = []
    
    for row in seat_types_data:
        # Get all trains of this type
        cursor.execute(
            "SELECT `train_number`, `departure_station_id`, `arrival_station_id` FROM `Trains` WHERE `train_type` = %s",
            (row['train_type'],)
        )
        trains = cursor.fetchall()
        
        for train_num, dep_id, arr_id in trains:
            if train_num not in train_numbers:
                continue
                
            # Add some random variation to base price
            base_price = float(row['base_price'])
            price = round(base_price * random.uniform(0.9, 1.1), 2)
            
            cursor.execute(
                "INSERT INTO `Prices` (`train_number`, `departure_station_id`, `arrival_station_id`, `seat_type`, `price`) VALUES (%s, %s, %s, %s, %s)",
                (train_num, dep_id, arr_id, row['seat_type'], price)
            )
            
            price_data.append({
                "train_number": train_num,
                "departure_station_id": dep_id,
                "arrival_station_id": arr_id,
                "seat_type": row['seat_type'],
                "price": price
            })
    
    print(f"Inserted {len(price_data)} prices")
    return price_data

def insert_salespersons_from_csv(cursor):
    """Insert salespersons from CSV file and return their IDs"""
    salespersons_data = read_csv_file('salespersons.csv')
    
    salesperson_ids = []
    for row in salespersons_data:
        cursor.execute(
            "INSERT INTO `Salespersons` (`salesperson_id`, `salesperson_name`, `contact_number`, `email`, `password_hash`, `role`) VALUES (%s, %s, %s, %s, %s, %s)",
            (row['salesperson_id'], row['salesperson_name'], row['contact_number'], 
             row['email'], row['password_hash'], row['role'])
        )
        salesperson_ids.append(row['salesperson_id'])
    
    print(f"Inserted {len(salespersons_data)} salespersons")
    return salesperson_ids

def insert_daily_train_status(cursor, train_numbers):
    """Insert sample daily train status"""
    status_data = []
    today = datetime.now().date()
    
    for train_num in train_numbers:
        # Get total seats for this train
        cursor.execute(
            "SELECT `total_seats` FROM `Trains` WHERE `train_number` = %s",
            (train_num,)
        )
        total_seats = cursor.fetchone()[0]
        
        # Create status for next 7 days
        for day in range(7):
            date = today + timedelta(days=day)
            remaining = random.randint(max(0, total_seats-50), total_seats)
            status_data.append((train_num, date, remaining))
    
    # Insert status
    for train_num, date, remaining in status_data:
        cursor.execute(
            "INSERT INTO `DailyTrainStatus` (`train_number`, `departure_date`, `remaining_seats`) VALUES (%s, %s, %s)",
            (train_num, date, remaining)
        )
    
    print(f"Inserted {len(status_data)} daily train status records")
    return status_data

def insert_sample_orders(cursor, train_numbers, station_ids, salesperson_ids, price_data):
    """Insert sample sales orders with guaranteed valid data"""
    orders = []
    id_types = ["ID Card", "Passport", "Driver License"]
    today = datetime.now().date()
    
    # Select 5 random price entries to create orders for
    selected_prices = random.sample(price_data, min(5, len(price_data)))
    
    for i, price_info in enumerate(selected_prices):
        train_num = price_info["train_number"]
        dep_id = price_info["departure_station_id"]
        arr_id = price_info["arrival_station_id"]
        seat_type = price_info["seat_type"]
        price = price_info["price"]
        
        # Find a date with available seats
        cursor.execute(
            "SELECT `departure_date` FROM `DailyTrainStatus` WHERE `train_number` = %s AND `remaining_seats` > 0 ORDER BY RAND() LIMIT 1",
            (train_num,)
        )
        result = cursor.fetchone()
        if not result:
            continue
            
        date = result[0]
        
        # Generate order details
        order_id = f"ORD{date.strftime('%Y%m%d')}{i:04d}"
        seat_num = f"{random.randint(1, 15)}{chr(random.randint(65, 70))}"
        passenger = f"Passenger_{i+1}"
        id_type = random.choice(id_types)
        id_num = f"{id_type[:2]}{random.randint(10000000, 99999999)}"
        sales_time = datetime.now() - timedelta(days=random.randint(0, 30))
        salesperson = random.choice(salesperson_ids)
        
        orders.append((
            order_id, train_num, date, seat_num, passenger, id_type, id_num,
            dep_id, arr_id, price, sales_time, salesperson
        ))
    
    # Insert orders
    if orders:
        for order in orders:
            cursor.execute("""
                INSERT INTO `SalesOrders` (
                    `order_id`, `train_number`, `departure_date`, `seat_number`, 
                    `passenger_name`, `id_type`, `id_number`, `departure_station_id`, 
                    `arrival_station_id`, `ticket_price`, `sales_time`, `salesperson_id`,
                    `order_status`
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'Sold')
            """, order)
        
        print(f"Inserted {len(orders)} sales orders")
        
        # Update remaining seats
        for order in orders:
            cursor.execute("""
                UPDATE `DailyTrainStatus`
                SET `remaining_seats` = `remaining_seats` - 1
                WHERE `train_number` = %s AND `departure_date` = %s
            """, (order[1], order[2]))
    else:
        print("No valid orders could be created")

def insert_refunds(cursor, salesperson_ids):
    """Insert sample refunds for some orders"""
    # Get some sold orders
    cursor.execute("""
        SELECT `order_id`, `train_number`, `departure_date`, `ticket_price`, `salesperson_id`
        FROM `SalesOrders` 
        WHERE `order_status` = 'Sold'
        LIMIT 3
    """)
    orders = cursor.fetchall()
    
    refunds = []
    for i, (order_id, train_num, date, price, original_salesperson) in enumerate(orders):
        refund_id = f"REF{date.strftime('%Y%m%d')}{i:04d}"
        refund_time = datetime.now() - timedelta(days=random.randint(0, 10))
        
        # 将 Decimal 转换为 float 进行计算
        price_float = float(price)
        refund_amount = round(price_float * random.uniform(0.7, 0.9), 2)  # 70-90% refund
        
        refund_salesperson = random.choice(salesperson_ids)
        
        refunds.append((refund_id, order_id, refund_time, refund_amount, refund_salesperson))
    
    # Insert refunds
    if refunds:
        for refund in refunds:
            cursor.execute("""
                INSERT INTO `Refunds` (
                    `refund_id`, `order_id`, `refund_time`, `refund_amount`, `salesperson_id`
                ) VALUES (%s, %s, %s, %s, %s)
            """, refund)
            
            # Update order status
            cursor.execute("""
                UPDATE `SalesOrders`
                SET `order_status` = 'Refunded'
                WHERE `order_id` = %s
            """, (refund[1],))
            
            # Update remaining seats
            cursor.execute("""
                UPDATE `DailyTrainStatus`
                SET `remaining_seats` = `remaining_seats` + 1
                WHERE `train_number` = %s AND `departure_date` = %s
            """, (orders[refunds.index(refund)][1], orders[refunds.index(refund)][2]))
        
        print(f"Inserted {len(refunds)} refunds")
    else:
        print("No orders available for refund")

if __name__ == "__main__":
    print("=== Inserting sample data ===")
    if insert_sample_data():
        print("Sample data insertion successful!")
    else:
        print("Sample data insertion failed.")