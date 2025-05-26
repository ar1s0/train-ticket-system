from database import db
from models import Train, Station, Price

class TrainService:
    @staticmethod
    def add_train(train_number, train_type, total_seats, dep_station_name, arr_station_name):
        dep_station = Station.find_one({'station_name': dep_station_name})
        arr_station = Station.find_one({'station_name': arr_station_name})
        if not dep_station or not arr_station:
            return False, "Departure or arrival station not found. Please add stations first."

        new_train = Train(
            train_number=train_number,
            train_type=train_type,
            total_seats=total_seats,
            departure_station_id=dep_station.station_id,
            arrival_station_id=arr_station.station_id
        )
        if new_train.save():
            return True, f"Train {train_number} added successfully."
        return False, "Failed to add train."

    @staticmethod
    def get_train_route(train_number):
        train = Train.find_one({'train_number': train_number})
        if not train:
            return [], f"Train {train_number} not found."

        stopovers_query = """
        SELECT 
            st.station_name,
            st.station_code,
            s.arrival_time,
            s.departure_time,
            s.stop_order
        FROM 
            Stopovers s
        JOIN 
            Stations st ON s.station_id = st.station_id
        WHERE 
            s.train_number = %s
        ORDER BY 
            s.stop_order
        """
        stopovers = db.execute_query(stopovers_query, (train_number,), fetch_all=True)

        route_data = []
        for i, stop in enumerate(stopovers):
            stop_type = "Stopover" 
            if i == 0: 
                stop_type = "Departure"
            elif i == len(stopovers) - 1:
                stop_type = "Arrival"

            route_data.append([
                i+1,
                stop['station_name'],
                stop['station_code'],
                stop['arrival_time'],
                stop['departure_time'],
                stop_type
            ])

        return route_data, None

    @staticmethod
    def list_all_trains():
        trains = Train.find_all()
        train_data = []
        
        if not trains:
            return train_data, "No trains found."

        for t in trains:
            dep_station = Station.find_one({'station_id': t.get('departure_station_id')})
            arr_station = Station.find_one({'station_id': t.get('arrival_station_id')})
            train_data.append([
                str(t.get('train_number', '')),
                str(t.get('train_type', '')),
                str(t.get('total_seats', '0')),
                dep_station.get('station_name', 'Unknown') if dep_station else 'Unknown',
                arr_station.get('station_name', 'Unknown') if arr_station else 'Unknown'
            ])
        return train_data, None

class StationService:
    @staticmethod
    def add_station(station_name, station_code=None):
        existing = Station.find_one({'station_name': station_name})
        if existing:
            return False, f"Station '{station_name}' already exists."

        new_station = Station(station_name=station_name, station_code=station_code)
        if new_station.save():
            return True, f"Station '{station_name}' added successfully."
        return False, f"Failed to add station '{station_name}'."

    @staticmethod
    def list_all_stations():
        stations = Station.find_all()
        station_data = []
        
        if not stations:
            return station_data, "No stations found."

        for s in stations:
            station_data.append([
                str(s.get('station_id', '')),
                str(s.get('station_name', '')),
                str(s.get('station_code', 'N/A'))
            ])
        return station_data, None

class PriceService:
    @staticmethod
    def add_price(train_number, dep_station_name, arr_station_name, price_amount):
        dep_station = Station.find_one({'station_name': dep_station_name})
        arr_station = Station.find_one({'station_name': arr_station_name})
        if not dep_station or not arr_station:
            return False, "Departure or arrival station not found for price rule."

        train = Train.find_one({'train_number': train_number})
        if not train:
            return False, f"Train {train_number} not found."

        new_price = Price(
            train_number=train_number,
            departure_station_id=dep_station.station_id,
            arrival_station_id=arr_station.station_id,
            price=price_amount
        )
        if new_price.save():
            return True, f"Price for {train_number} ({dep_station_name}-{arr_station_name}) added successfully."
        return False, "Failed to add price rule."

    @staticmethod
    def list_prices_for_train(train_number):
        prices = Price.find_all({'train_number': train_number})
        price_data = []
        
        if not prices:
            return price_data, f"No prices found for train {train_number}."

        for p in prices:
            dep_station = Station.find_one({'station_id': p.get('departure_station_id')})
            arr_station = Station.find_one({'station_id': p.get('arrival_station_id')})
            price_data.append([
                dep_station.get('station_name', 'Unknown') if dep_station else 'Unknown',
                arr_station.get('station_name', 'Unknown') if arr_station else 'Unknown',
                f"${float(p.get('price', 0)):.2f}"
            ])
        return price_data, None


    @staticmethod
    def search_available_tickets(dep_station_name, arr_station_name, departure_date=None):
        """
        查询所有经过指定起点和终点站点的列车信息，按列车分类
        
        参数:
            dep_station_name: 起点站名
            arr_station_name: 终点站名
            departure_date: 可选，指定出发日期
        
        返回:
            包含符合条件的列车信息的列表，以及错误信息(如果有)
        """
        # 验证车站是否存在
        dep_station = Station.find_one({'station_name': dep_station_name})
        arr_station = Station.find_one({'station_name': arr_station_name})
        if not dep_station or not arr_station:
            return [], "Departure or arrival station not found."

        # 获取所有列车信息
        train_query = "SELECT * FROM Trains"
        all_trains = db.execute_query(train_query, fetch_all=True)
        
        if not all_trains:
            return [], "No trains found in the system."

        train_data = []
        
        for train in all_trains:
            # 检查该列车是否经过起点站和终点站
            check_stop_query = """
            SELECT 
                dep.stop_order as dep_stop_order,
                dep.departure_time as departure_time,
                dep.seats as dep_seats,
                arr.stop_order as arr_stop_order,
                arr.arrival_time as arrival_time
            FROM 
                (SELECT stop_order, departure_time, seats
                 FROM Stopovers 
                 WHERE train_number = %s AND station_id = %s) as dep,
                (SELECT stop_order, arrival_time 
                 FROM Stopovers 
                 WHERE train_number = %s AND station_id = %s) as arr
            """
            stop_params = (
                train['train_number'], 
                dep_station.get('station_id'),
                train['train_number'], 
                arr_station.get('station_id')
            )
            stop_result = db.execute_query(check_stop_query, stop_params, fetch_one=True)
            
            # 如果列车不经过这两个站点或顺序不对，跳过
            if not stop_result or not stop_result['dep_stop_order'] or not stop_result['arr_stop_order']:
                continue
            if stop_result['dep_stop_order'] >= stop_result['arr_stop_order']:
                continue

            print(f"Train {train['train_number']} passes through {dep_station_name} and {arr_station_name}.")
            
            # 获取该列车的停靠站总数
            stopover_count_query = "SELECT COUNT(*) AS count FROM Stopovers WHERE train_number = %s"

            stopover_count = db.execute_query(stopover_count_query, (train['train_number'],), fetch_one=True)['count']

            # 获取价格信息
            price_query = """
            SELECT price
            FROM Prices
            WHERE train_number = %s
            AND departure_station_id = %s
            AND arrival_station_id = %s
            """
            price_params = (train['train_number'], train['departure_station_id'], train['arrival_station_id'])
            prices = db.execute_query(price_query, price_params, fetch_all=True)

            print(f"Prices for train {train['train_number']}: {prices}")
            print(f"Stopover count: {stopover_count}")
            print(f"Departure stop order: {stop_result['dep_stop_order']}, Arrival stop order: {stop_result['arr_stop_order']}")
            price = float(prices[0]['price']) * (stop_result['arr_stop_order'] - stop_result['dep_stop_order']) / (stopover_count - 1)
            # 保留一位小数
            price = round(price, 1)

            # 获取指定日期的剩余座位数
            remaining_seats = None
            if departure_date:
                seats_query = """
                SELECT remaining_seats
                FROM DailyTrainStatus
                WHERE train_number = %s
                AND departure_date = %s
                """
                seats_result = db.execute_query(seats_query, (train['train_number'], departure_date), fetch_one=True)
                remaining_seats = seats_result['remaining_seats'] if seats_result else 0

                # 如果指定了日期但没有剩余座位，跳过
                if remaining_seats == 0:
                    continue

            # 构建列车信息
            train_info = [
                train['train_number'],
                dep_station_name,
                stop_result['departure_time'],
                arr_station_name,
                stop_result['arrival_time'],
                price,
                stop_result['dep_seats'],
                train['train_type']
            ]
            train_data.append(train_info)

        if not train_data:
            return [], "No trains found passing through both stations in the correct order."

        return train_data, None

