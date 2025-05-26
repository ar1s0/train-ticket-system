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

        print(f"Train: {row['train_number']}, Station: {row['station_name']}, Arrival: {arrival_time}, Departure: {departure_time}, Stop Order: {row['stop_order']}")
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



if __name__ == "__main__":
    print("=== Inserting sample data ===")
    if insert_sample_data():
        print("Sample data insertion successful!")
    else:
        print("Sample data insertion failed.")