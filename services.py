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
            departure_date: 可选，指定出发日期 (格式: YYYY-MM-DD)
        
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
            # 修改查询以获取途经站点的座位信息
            check_stop_query = """
            WITH RECURSIVE route_stops AS (
                SELECT 
                    s1.stop_order, 
                    s1.station_id,
                    s1.seats,
                    s1.departure_time
                FROM Stopovers s1
                WHERE s1.train_number = %s 
                AND s1.station_id = %s
                {date_condition}
                
                UNION ALL
                
                SELECT 
                    s2.stop_order,
                    s2.station_id,
                    s2.seats,
                    s2.departure_time
                FROM Stopovers s2
                JOIN route_stops rs ON s2.train_number = %s 
                AND s2.stop_order = rs.stop_order + 1
                WHERE s2.train_number = %s
            )
            SELECT 
                MIN(rs.seats) as min_seats,
                MIN(rs.stop_order) as dep_stop_order,
                MAX(rs.stop_order) as arr_stop_order,
                (SELECT departure_time 
                 FROM Stopovers 
                 WHERE train_number = %s 
                 AND station_id = %s) as departure_time,
                (SELECT arrival_time 
                 FROM Stopovers 
                 WHERE train_number = %s 
                 AND station_id = %s) as arrival_time
            FROM route_stops rs
            WHERE rs.stop_order BETWEEN 
                (SELECT stop_order FROM Stopovers WHERE train_number = %s AND station_id = %s) 
                AND 
                (SELECT stop_order FROM Stopovers WHERE train_number = %s AND station_id = %s)
            """
            
            # 构建查询参数
            stop_params = [
                train['train_number'],
                dep_station.get('station_id')
            ]
            
            # 如果指定了出发日期，添加日期条件
            date_condition = ""
            if departure_date:
                date_condition = "AND DATE(departure_time) = %s"
                stop_params.extend([departure_date])
                
            # 添加其余参数
            stop_params.extend([
                train['train_number'],
                train['train_number'],
                train['train_number'],
                dep_station.get('station_id'),
                train['train_number'],
                arr_station.get('station_id'),
                train['train_number'],
                dep_station.get('station_id'),
                train['train_number'],
                arr_station.get('station_id')
            ])
            
            check_stop_query = check_stop_query.format(date_condition=date_condition)
            stop_result = db.execute_query(check_stop_query, tuple(stop_params), fetch_one=True)
            
            # 如果列车不经过这两个站点或顺序不对，跳过
            if not stop_result or not stop_result['dep_stop_order'] or not stop_result['arr_stop_order']:
                continue
            if stop_result['dep_stop_order'] >= stop_result['arr_stop_order']:
                continue

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

            price = float(prices[0]['price']) * (stop_result['arr_stop_order'] - stop_result['dep_stop_order']) / (stopover_count - 1)
            price = round(price, 1)

            # 构建列车信息时使用最小座位数
            train_info = [
                train['train_number'],
                dep_station_name,
                stop_result['departure_time'],
                arr_station_name,
                stop_result['arrival_time'],
                price,
                stop_result['min_seats'],  # 使用计算得到的最小座位数
                train['train_type']
            ]
            train_data.append(train_info)

        if not train_data:
            return [], "No trains found passing through both stations in the correct order."

        return train_data, None

class OrderService:
    @staticmethod
    def create_order(train_number, train_type, departure_station, arrival_station, 
                    price, customer_name, customer_id_card):
        """创建订单"""
        try:
            # 验证客户信息
            customer_query = """
            SELECT * FROM Customers 
            WHERE name = %s AND id_card = %s
            """
            customer = db.execute_query(
                customer_query, 
                (customer_name, customer_id_card),
                fetch_one=True
            )
            
            if not customer:
                return False, "Customer information not found or incorrect."
            
            # 生成订单号 (年月日时分秒+4位随机数)
            import datetime
            import random
            order_id = datetime.datetime.now().strftime('%Y%m%d%H%M%S') + \
                      str(random.randint(1000, 9999))
            
            # 插入订单
            order_query = """
            INSERT INTO SalesOrders (
                order_id, train_number, train_type,
                departure_station, arrival_station,
                price, customer_name, customer_phone, 
                operation_type, status
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, 
                'Booking', 'Ready'
            )
            """
            
            # 执行订单插入
            db.execute_query(
                order_query,
                (order_id, train_number, train_type,
                 departure_station, arrival_station,
                 price, customer_name, customer['phone'])
            )
            
            return True, f"Order created successfully! Order ID: {order_id}"
            
        except Exception as e:
            return False, f"Failed to create order: {str(e)}"
    
    @staticmethod
    def get_orders_by_passenger(name, phone):
        """根据乘客信息查询订单"""
        try:
            print(f"Querying orders for passenger {name} {phone}")
            query = """
                SELECT *
                FROM SalesOrders 
                WHERE customer_name = %s 
                AND customer_phone = %s
                ORDER BY operation_time DESC
            """
            
            orders = db.execute_query(query, (name, phone), fetch_all=True)

            if not orders:
                return [], "No orders found for this passenger"

            orders_data = []
            for order in orders:
                orders_data.append([
                    order['order_id'],
                    order['train_number'],
                    order['train_type'],
                    order['departure_station'],
                    order['arrival_station'],
                    f"${float(order['price']):.2f}",
                    order['customer_name'],
                    order['customer_phone'],
                    order['operation_type'],
                    order['operation_time'].strftime('%Y-%m-%d %H:%M:%S'),
                    order['status']
                ])

            for order in orders_data:
                print(order)
                
            return orders_data, None
            
        except Exception as e:
            return [], f"Error querying orders: {str(e)}"

