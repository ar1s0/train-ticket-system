from database import db
from models import Train, Station, Price
from mysql.connector import Error

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
    def get_train_route(train_number, departure_date=None):
        """获取列车路线信息
    
        Args:
            train_number (str): 列车号
            departure_date (str, optional): 发车日期，格式YYYY-MM-DD
        
        Returns:
            tuple: (route_data, error_message)
                route_data: 包含以下字段的列表:
                    - train_number: 列车号
                    - start_date: 发车日期
                    - station_name: 站点名称
                    - station_code: 站点代码
                    - arrival_time: 到达时间
                    - departure_time: 出发时间
                    - stop_type: 站点类型
                    - stop_order: 站点顺序
                    - sold_tickets: 已售票数
        """
        try:
            result = db.call_proc('sp_get_train_route', (train_number, departure_date))
            
            if not result:
                error_msg = "No route information found"
                if departure_date:
                    error_msg += f" for date {departure_date}"
                return [], error_msg

            route_data = []
            for stop in result:
                arrival_time = stop['arrival_time'].strftime('%Y-%m-%d %H:%M:%S') if stop['arrival_time'] else '-'
                departure_time = stop['departure_time'].strftime('%Y-%m-%d %H:%M:%S') if stop['departure_time'] else '-'
                
                route_data.append([
                    stop['train_number'],
                    stop['start_date'].strftime('%Y-%m-%d'),  # 添加发车日期
                    stop['station_name'],
                    stop['station_code'] or '-',
                    arrival_time,
                    departure_time,
                    stop['stop_type'],
                    stop['stop_order'],
                    stop['sold_tickets']
                ])

            return route_data, None
            
        except Exception as e:
            return [], f"Error getting train route: {str(e)}"

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


class TicketService:
    @staticmethod
    def search_available_tickets(dep_station_name, arr_station_name, departure_date=None):
        """
        查询所有经过指定起点和终点站点的列车信息，按列车和发车日期分组
    
        参数:
            dep_station_name: 起点站名
            arr_station_name: 终点站名
            departure_date: 可选，指定出发日期 (格式: YYYY-MM-DD)
    
        返回:
            包含符合条件的列车信息的列表，以及错误信息(如果有)
        """
        # Step 1: 验证车站是否存在
        dep_station = Station.find_one({'station_name': dep_station_name})
        arr_station = Station.find_one({'station_name': arr_station_name})
        if not dep_station or not arr_station:
            return [], "Departure or arrival station not found."
        
        # Step 2: 构建日期过滤条件
        date_filter = ""
        params = []
        if departure_date:
            date_filter = "AND DATE(s1.departure_time) = %s"
            params.append(departure_date)
        
        # Step 3: 查询所有经过起点站的列车和发车日期
        trains_through_dep_query = """
        SELECT DISTINCT train_number, start_date
        FROM Stopovers
        WHERE station_id = %s
        """ + date_filter
        
        params.insert(0, dep_station.get('station_id'))
        trains_through_dep = db.execute_query(trains_through_dep_query, tuple(params), fetch_all=True)
        
        if not trains_through_dep:
            return [], "No trains found passing through the departure station."
        
        # Step 4: 对每个列车和日期组合验证是否经过终点站
        train_data = []
        
        for train_info in trains_through_dep:
            train_number = train_info['train_number']
            start_date = train_info['start_date']
            
            # Step 4.1: 获取两个站点的停靠信息
            route_query = """
            SELECT 
                s1.stop_order as dep_stop_order,
                s2.stop_order as arr_stop_order,
                s1.departure_time,
                s2.arrival_time,
                MIN(s3.seats) as min_seats,
                t.train_type
            FROM 
                Stopovers s1
                JOIN Stopovers s2 ON s1.train_number = s2.train_number AND s1.start_date = s2.start_date
                JOIN Stopovers s3 ON s1.train_number = s3.train_number AND s1.start_date = s3.start_date
                JOIN Trains t ON s1.train_number = t.train_number
            WHERE 
                s1.train_number = %s
                AND s1.start_date = %s
                AND s1.station_id = %s
                AND s2.station_id = %s
                AND s3.stop_order >= s1.stop_order
                AND s3.stop_order < s2.stop_order
            GROUP BY
                s1.stop_order, s2.stop_order, s1.departure_time, s2.arrival_time, t.train_type
            HAVING
                dep_stop_order < arr_stop_order
            """
            
            route_info = db.execute_query(
                route_query,
                (train_number, start_date, dep_station.get('station_id'), arr_station.get('station_id')),
                fetch_one=True
            )
            
            # 如果没有找到路线或者顺序不对，跳过
            if not route_info:
                continue
            
            # Step 4.2: 获取站点总数以计算价格比例
            stopover_count_query = """
            SELECT COUNT(*) AS count 
            FROM Stopovers 
            WHERE train_number = %s 
            AND start_date = %s
            """
            
            stopover_count = db.execute_query(
                stopover_count_query,
                (train_number, start_date),
                fetch_one=True
            )['count']
            
            # Step 4.3: 获取票价信息
            price_query = """
            SELECT price
            FROM Prices
            WHERE train_number = %s
            AND departure_station_id = %s
            AND arrival_station_id = %s
            """
            
            price_result = db.execute_query(
                price_query,
                (train_number, dep_station.get('station_id'), arr_station.get('station_id')),
                fetch_one=True
            )
            
            if not price_result:
                # 如果没有直达价格，尝试计算比例价格
                base_price_query = """
                SELECT price
                FROM Prices
                WHERE train_number = %s
                LIMIT 1
                """
                
                base_price_result = db.execute_query(
                    base_price_query,
                    (train_number,),
                    fetch_one=True
                )
                
                if not base_price_result:
                    continue  # 没有价格信息，跳过
                
                # 按站点比例计算价格
                segment_ratio = (route_info['arr_stop_order'] - route_info['dep_stop_order']) / (stopover_count - 1)
                price = float(base_price_result['price']) * segment_ratio
            else:
                price = float(price_result['price'])
            
            # 四舍五入到一位小数
            price = round(price, 1)
            
            # Step 5: 添加到结果列表
            train_info = [
                train_number,
                start_date.strftime('%Y-%m-%d'),
                dep_station_name,
                route_info['departure_time'].strftime('%Y-%m-%d %H:%M:%S') if route_info['departure_time'] else '-',
                arr_station_name,
                route_info['arrival_time'].strftime('%Y-%m-%d %H:%M:%S') if route_info['arrival_time'] else '-',
                price,
                route_info['min_seats'],
                route_info['train_type']
            ]
            
            train_data.append(train_info)
        
        if not train_data:
            return [], "No trains found passing through both stations in the correct order."
        
        # 按出发时间排序
        train_data.sort(key=lambda x: x[3])
        return train_data, None

class OrderService:
    @staticmethod
    def create_order(train_number, train_type, start_date, departure_station, arrival_station, 
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
                order_id, train_number, train_type, start_date,
                departure_station, arrival_station,
                price, customer_name, customer_phone, 
                operation_type, status
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, 
                'Booking', 'Ready'
            )
            """
            
            # 执行订单插入
            db.execute_query(
                order_query,
                (order_id, train_number, train_type, start_date,
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
                
            return orders_data, None
            
        except Exception as e:
            return [], f"Error querying orders: {str(e)}"
    
    @staticmethod
    def cancel_order(order_id):
        """取消订单"""
        try:
            # 检查订单状态
            check_query = """
            SELECT status FROM SalesOrders 
            WHERE order_id = %s
            """
            order = db.execute_query(check_query, (order_id,), fetch_one=True)
            
            if not order:
                return False, "Order not found"
            
            if order['status'] != 'Ready':
                return False, "Only orders in Ready status can be cancelled"
            
            # 更新订单状态
            update_query = """
            UPDATE SalesOrders 
            SET status = 'Cancelled'
            WHERE order_id = %s
            """
            db.execute_query(update_query, (order_id,))
            
            return True, "Order cancelled successfully"
            
        except Exception as e:
            return False, f"Failed to cancel order: {str(e)}"

    @staticmethod
    def request_refund(order_id):
        """申请退款"""
        try:
            # 检查订单状态
            check_query = """
            SELECT status FROM SalesOrders 
            WHERE order_id = %s
            """
            order = db.execute_query(check_query, (order_id,), fetch_one=True)
            
            if not order:
                return False, "Order not found"
            
            if order['status'] != 'Success':
                return False, "Only successful orders can request refund"
            
            # 更新订单状态为待退款
            update_query = """
            UPDATE SalesOrders 
            SET status = 'RefundPending',
                operation_type = 'Refund'
            WHERE order_id = %s
            """
            db.execute_query(update_query, (order_id,))
            
            return True, "Refund request submitted successfully"
            
        except Exception as e:
            return False, f"Failed to request refund: {str(e)}"

    @staticmethod
    def get_pending_orders():
        """获取待处理订单"""
        try:
            query = """
                SELECT * FROM PendingOrdersView
            """
            orders = db.execute_query(query, fetch_all=True)

            if not orders:
                return [], "No pending orders found"

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
                
            return orders_data, None
            
        except Exception as e:
            return [], f"Error querying orders: {str(e)}"

    @staticmethod
    def process_order(order_id, approve=True, salesperson_id=None):
        """处理订单（确认或拒绝）
        
        Args:
            order_id (str): 订单ID
            approve (bool): True为批准，False为拒绝
            salesperson_id (str): 处理订单的乘务员ID
        """
        try:
            # 检查订单状态和信息
            check_query = """
            SELECT status, operation_type, price, 
                   train_number, start_date, departure_station, arrival_station 
            FROM SalesOrders 
            WHERE order_id = %s
            """
            order = db.execute_query(check_query, (order_id,), fetch_one=True)
            
            if not order:
                return False, "Order not found"
            
            if order['status'] not in ('Ready', 'RefundPending'):
                return False, "Order cannot be processed in current status"
            
            # 确定新状态和操作类型
            original_status = order['status']
            operation_type = 'Approve' if approve else 'Reject'
            
            # 如果是批准新订单，需要检查余票
            if approve and original_status == 'Ready':
                # 检查所有经过站点是否有余票
                check_seats_query = """
                SELECT MIN(s.seats) as min_seats
                FROM Stopovers s
                JOIN Stations st1 ON st1.station_name = %s
                JOIN Stations st2 ON st2.station_name = %s
                WHERE s.train_number = %s
                AND s.start_date = %s
                AND s.stop_order >= (
                    SELECT stop_order 
                    FROM Stopovers s2 
                    JOIN Stations st3 ON st3.station_id = s2.station_id 
                    WHERE st3.station_name = %s 
                    AND s2.train_number = %s
                    AND s2.start_date = %s
                )
                AND s.stop_order < (
                    SELECT stop_order 
                    FROM Stopovers s3 
                    JOIN Stations st4 ON st4.station_id = s3.station_id 
                    WHERE st4.station_name = %s 
                    AND s3.train_number = %s
                    AND s3.start_date = %s
                )
                """
                
                seats_result = db.execute_query(
                    check_seats_query, 
                    (order['departure_station'], order['arrival_station'],
                     order['train_number'], order['start_date'],
                     order['departure_station'], order['train_number'], order['start_date'],
                     order['arrival_station'], order['train_number'], order['start_date']),
                    fetch_one=True
                )
                
                if not seats_result or seats_result['min_seats'] <= 0:
                    return False, "No available seats for this route"
        
            if original_status == 'Ready':
                new_status = 'Success' if approve else 'Cancelled'
            else:
                new_status = 'Refunded' if approve else 'Success'
            
            # 生成操作备注
            remarks = None
            if original_status == 'Ready':
                remarks = f"Order {'approved' if approve else 'rejected'} by salesperson"
            else:
                remarks = f"Refund request {'approved' if approve else 'rejected'} by salesperson"
            
            # 更新订单状态
            update_query = """
            UPDATE SalesOrders 
            SET status = %s
            WHERE order_id = %s
            """
            db.execute_query(update_query, (new_status, order_id))
            
            # 记录操作
            success = OrderService.record_operation(
                order_id=order_id,
                salesperson_id=salesperson_id,
                operation_type=operation_type,
                original_status=original_status,
                new_status=new_status,
                price=float(order['price']),
                remarks=remarks
            )
            
            if not success:
                return False, "Operation recorded but failed to log the operation"
            
            return True, f"Order {new_status.lower()} successfully"
            
        except Exception as e:
            return False, f"Failed to process order: {str(e)}"
    
    @staticmethod
    def record_operation(order_id, salesperson_id, operation_type, 
                    original_status, new_status, price, remarks=None):
        """记录订单操作历史
        
        Args:
            order_id (str): 订单ID
            salesperson_id (str): 操作人员ID
            operation_type (str): 操作类型 ('Approve', 'Reject', 'Process_Refund')
            original_status (str): 原始状态
            new_status (str): 新状态
            price (decimal): 操作涉及的金额
            remarks (str, optional): 备注说明

        Returns:
            bool: 操作是否成功
        """
        try:
            query = """
                INSERT INTO OrderOperations (
                    order_id,
                    salesperson_id,
                    operation_type,
                    original_status,
                    new_status,
                    price,
                    operation_time,
                    remarks
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, %s
                )
            """
            db.execute_query(
                query,
                (order_id, salesperson_id, operation_type, 
                 original_status, new_status, price, remarks)
            )
            return True
        except Exception as e:
            print(f"Error recording operation: {e}")
            return False

class SalespersonService:
    @staticmethod
    def verify_credentials(salesperson_id, password):
        """验证乘务员凭据"""
        try:
            query = """
            SELECT salesperson_id, salesperson_name, role
            FROM Salespersons 
            WHERE salesperson_id = %s AND password = %s
            """

            result = db.execute_query(query, (salesperson_id, password), fetch_one=True)

            if result:
                return True, result
            return False, "Invalid credentials"
            
        except Exception as e:
            return False, f"Error verifying credentials: {str(e)}"
    
    @staticmethod
    def get_daily_sales_report(report_date, staff_id=None):
        """获取指定日期的销售报表
        
        Args:
            report_date (str): 报表日期，格式为YYYY-MM-DD
            staff_id (str, optional): 指定乘务员ID，为空时显示所有乘务员
            
        Returns:
            tuple: (data, error_message)
        """
        try:
            if staff_id:
                result = db.call_proc('sp_daily_staff_report', (report_date, staff_id))
            else:
                result = db.call_proc('sp_daily_sales_report', (report_date,))

            if result:
                data = [
                    [
                        str(row['salesperson_id']),
                        str(row['salesperson_name']),
                        str(row['total_orders']),
                        f"${float(row['booking_revenue'] or 0):.2f}",
                        f"${float(row['refund_amount'] or 0):.2f}"
                    ]
                    for row in result
                ]
                return data, None
                
            return [], "No data found"
            
        except Exception as e:
            return None, str(e)
