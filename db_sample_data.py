# db_sample_data.py

import mysql.connector
from mysql.connector import Error
from db_config import DB_CONFIG
import random
from datetime import datetime, timedelta

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
        station_ids = insert_stations(cursor)
        train_numbers = insert_trains(cursor, station_ids)
        insert_stopovers(cursor, train_numbers, station_ids)
        price_data = insert_prices(cursor, train_numbers, station_ids)
        salesperson_ids = insert_salespersons(cursor)
        daily_status = insert_daily_train_status(cursor, train_numbers)
        
        # Insert sales orders with guaranteed valid data
        insert_sales_orders(cursor, train_numbers, station_ids, salesperson_ids, price_data)
        
        # Insert refunds for some orders
        insert_refunds(cursor, salesperson_ids)
        
        conn.commit()
        print("✅ Sample data inserted successfully!")
        return True
        
    except Error as e:
        conn.rollback()
        print(f"❌ Error inserting sample data: {e}")
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
            print(f"🧹 Cleared data from {table}")
        except Error as e:
            print(f"⚠️ Error clearing {table}: {e}")
    
    # Re-enable foreign key checks
    cursor.execute("SET FOREIGN_KEY_CHECKS = 1")

def insert_stations(cursor):
    """Insert sample stations and return station_id mapping"""
    stations = [
        ("Beijing", "BJ"),
        ("Shanghai", "SH"),
        ("Guangzhou", "GZ"),
        ("Shenzhen", "SZ"),
        ("Chengdu", "CD"),
        ("Chongqing", "CQ"),
        ("Hangzhou", "HZ"),
        ("Wuhan", "WH"),
        ("Xi'an", "XA"),
        ("Nanjing", "NJ")
    ]
    
    station_ids = {}
    for name, code in stations:
        cursor.execute(
            "INSERT INTO `Stations` (`station_name`, `station_code`) VALUES (%s, %s)",
            (name, code)
        )
        station_id = cursor.lastrowid
        station_ids[name] = station_id
    
    print(f"🚉 Inserted {len(stations)} stations")
    return station_ids

def insert_trains(cursor, station_ids):
    """Insert sample trains and return train numbers"""
    trains = [
        ("G1", "High-Speed", 500, "Beijing", "Shanghai"),
        ("G2", "High-Speed", 500, "Shanghai", "Beijing"),
        ("D3", "Bullet", 400, "Beijing", "Guangzhou"),
        ("D4", "Bullet", 400, "Guangzhou", "Beijing"),
        ("K5", "Express", 300, "Guangzhou", "Shenzhen"),
        ("K6", "Express", 300, "Shenzhen", "Guangzhou"),
        ("T7", "Fast", 350, "Beijing", "Chengdu"),
        ("T8", "Fast", 350, "Chengdu", "Beijing"),
        ("Z9", "Direct", 200, "Shanghai", "Chongqing"),
        ("Z10", "Direct", 200, "Chongqing", "Shanghai")
    ]
    
    train_numbers = []
    for number, train_type, seats, dep_station, arr_station in trains:
        dep_id = station_ids[dep_station]
        arr_id = station_ids[arr_station]
        
        cursor.execute(
            "INSERT INTO `Trains` (`train_number`, `train_type`, `total_seats`, `departure_station_id`, `arrival_station_id`) VALUES (%s, %s, %s, %s, %s)",
            (number, train_type, seats, dep_id, arr_id)
        )
        train_numbers.append(number)
    
    print(f"🚆 Inserted {len(trains)} trains")
    return train_numbers

def insert_stopovers(cursor, train_numbers, station_ids):
    """Insert sample stopovers"""
    stopovers = [
        ("G1", "Hangzhou", "08:30:00", "08:33:00", 2),
        ("G1", "Wuhan", "09:45:00", "09:48:00", 3),
        ("D3", "Xi'an", "12:15:00", "12:20:00", 2),
        ("D3", "Nanjing", "14:30:00", "14:35:00", 3),
        ("T7", "Hangzhou", "10:00:00", "10:05:00", 2),
        ("T7", "Wuhan", "13:30:00", "13:35:00", 3),
        ("Z9", "Shenzhen", "16:45:00", "16:50:00", 2),
        ("Z9", "Chengdu", "19:30:00", "19:35:00", 3)
    ]
    
    for train_num, station_name, arr_time, dep_time, stop_order in stopovers:
        if train_num not in train_numbers:
            continue
            
        station_id = station_ids.get(station_name)
        if not station_id:
            continue
            
        cursor.execute(
            "INSERT INTO `Stopovers` (`train_number`, `station_id`, `arrival_time`, `departure_time`, `stop_order`) VALUES (%s, %s, %s, %s, %s)",
            (train_num, station_id, arr_time, dep_time, stop_order)
        )
    
    print(f"🛑 Inserted {len(stopovers)} stopovers")

def insert_prices(cursor, train_numbers, station_ids):
    """Insert sample prices and return price data"""
    seat_types = [
        "Hard Seat", "Soft Seat", "Hard Sleeper", 
        "Soft Sleeper", "Business Class", "First Class", "Second Class"
    ]
    
    price_data = []
    base_prices = {
        "High-Speed": {"Business Class": 500, "First Class": 300, "Second Class": 150},
        "Bullet": {"Business Class": 400, "First Class": 250, "Second Class": 120},
        "Express": {"Hard Seat": 80, "Soft Seat": 120, "Hard Sleeper": 180},
        "Fast": {"Hard Seat": 70, "Soft Seat": 110, "Hard Sleeper": 160, "Soft Sleeper": 220},
        "Direct": {"Hard Sleeper": 150, "Soft Sleeper": 250}
    }
    
    for train_num in train_numbers[:5]:  # Only price some trains for demo
        # Get train type and route
        cursor.execute(
            "SELECT `train_type`, `departure_station_id`, `arrival_station_id` FROM `Trains` WHERE `train_number` = %s",
            (train_num,)
        )
        train_type, dep_id, arr_id = cursor.fetchone()
        
        # Add prices based on train type
        for seat_type in seat_types:
            # Get base price for this train type and seat type
            base_price = base_prices.get(train_type, {}).get(seat_type)
            if base_price is None:
                # Default pricing if not specified
                if "Seat" in seat_type:
                    base_price = random.randint(50, 150)
                elif "Sleeper" in seat_type:
                    base_price = random.randint(150, 300)
                else:
                    base_price = random.randint(200, 500)
            
            # Add some random variation
            price = base_price * random.uniform(0.9, 1.1)
            price = round(price, 2)
            
            cursor.execute(
                "INSERT INTO `Prices` (`train_number`, `departure_station_id`, `arrival_station_id`, `seat_type`, `price`) VALUES (%s, %s, %s, %s, %s)",
                (train_num, dep_id, arr_id, seat_type, price)
            )
            
            price_data.append({
                "train_number": train_num,
                "departure_station_id": dep_id,
                "arrival_station_id": arr_id,
                "seat_type": seat_type,
                "price": price
            })
    
    print(f"💰 Inserted {len(price_data)} prices")
    return price_data

def insert_salespersons(cursor):
    """Insert sample salespersons and return their IDs"""
    salespersons = [
        ("SP001", "Zhang Wei", "13800138001", "zhang.wei@example.com", "1", "Admin"),
        ("SP002", "Li Na", "13800138002", "li.na@example.com", "2", "Salesperson"),
        ("SP003", "Wang Fang", "13800138003", "wang.fang@example.com", "3", "Salesperson"),
        ("SP004", "Liu Yang", "13800138004", "liu.yang@example.com", "4", "Salesperson"),
        ("SP005", "Chen Hao", "13800138005", "chen.hao@example.com", "5", "Salesperson")
    ]
    
    salesperson_ids = []
    for sp_id, name, contact, email, pwd, role in salespersons:
        cursor.execute(
            "INSERT INTO `Salespersons` (`salesperson_id`, `salesperson_name`, `contact_number`, `email`, `password_hash`, `role`) VALUES (%s, %s, %s, %s, %s, %s)",
            (sp_id, name, contact, email, pwd, role)
        )
        salesperson_ids.append(sp_id)
    
    print(f"👔 Inserted {len(salespersons)} salespersons")
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
            remaining = random.randint(max(0, total_seats-50), total_seats)  # Ensure some seats available
            status_data.append((train_num, date, remaining))
    
    # Insert status
    for train_num, date, remaining in status_data:
        cursor.execute(
            "INSERT INTO `DailyTrainStatus` (`train_number`, `departure_date`, `remaining_seats`) VALUES (%s, %s, %s)",
            (train_num, date, remaining)
        )
    
    print(f"📅 Inserted {len(status_data)} daily train status records")
    return status_data

def insert_sales_orders(cursor, train_numbers, station_ids, salesperson_ids, price_data):
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
        
        print(f"🎫 Inserted {len(orders)} sales orders")
        
        # Update remaining seats
        for order in orders:
            cursor.execute("""
                UPDATE `DailyTrainStatus`
                SET `remaining_seats` = `remaining_seats` - 1
                WHERE `train_number` = %s AND `departure_date` = %s
            """, (order[1], order[2]))
    else:
        print("⚠️ No valid orders could be created")

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
        
        print(f"💸 Inserted {len(refunds)} refunds")
    else:
        print("⚠️ No orders available for refund")

if __name__ == "__main__":
    print("=== Inserting sample data ===")
    if insert_sample_data():
        print("✅ Sample data insertion successful!")
    else:
        print("❌ Sample data insertion failed.")