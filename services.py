# services.py

import datetime
from database import db
from models import Train, Station, Price, SalesOrder, Refund, DailyTrainStatus, Salesperson


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
    def update_train(train_number, new_total_seats=None):
        train = Train.find_one({'train_number': train_number})
        if not train:
            return False, f"Train {train_number} not found."

        train_obj = Train(**train)
        if new_total_seats is not None:
            train_obj.total_seats = new_total_seats

        if train_obj.save():
            return True, f"Train {train_number} updated successfully."
        return False, f"Failed to update train {train_number}."

    @staticmethod
    def delete_train(train_number):
        if Train.delete({'train_number': train_number}):
            return True, f"Train {train_number} deleted successfully."
        return False, f"Failed to delete train {train_number}."
        
    @staticmethod
    def get_train_route(train_number):
        """获取列车的完整行车轨迹，包括起点、终点和所有中间站"""
        # 验证列车是否存在
        train = Train.find_one({'train_number': train_number})
        if not train:
            return [], f"Train {train_number} not found."

        # 查询所有停靠站（按顺序）
        stopovers_query = """
        SELECT 
            st.station_name,
            st.station_code,
            s.arrival_time AS arrival_time,
            s.departure_time AS departure_time,
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

        # 构建完整路线
        route_data = []

        for i, stop in enumerate(stopovers):
            route_data.append([
                i+1,  # 顺序号
                stop['station_name'],
                stop['station_code'],
                stop['arrival_time'],
                stop['departure_time'],
                "Stopover"
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
        # 检查是否已存在同名车站
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
    def add_price(train_number, dep_station_name, arr_station_name, seat_type, price_amount):
        dep_station = Station.find_one({'station_name': dep_station_name})
        arr_station = Station.find_one({'station_name': arr_station_name})
        if not dep_station or not arr_station:
            return False, "Departure or arrival station not found for price rule."

        train = Train.find_one({'train_number': train_number})
        if not train:
            return False, f"Train {train_number} not found."

        # 检查是否已存在相同价格规则
        existing = Price.find_one({
            'train_number': train_number,
            'departure_station_id': dep_station.station_id,
            'arrival_station_id': arr_station.station_id,
            'seat_type': seat_type
        })
        if existing:
            return False, "Price rule already exists for this route and seat type."

        new_price = Price(
            train_number=train_number,
            departure_station_id=dep_station.station_id,
            arrival_station_id=arr_station.station_id,
            seat_type=seat_type,
            price=price_amount
        )
        if new_price.save():
            return True, f"Price for {train_number} ({dep_station_name}-{arr_station_name}, {seat_type}) added successfully."
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
                str(p.get('seat_type', '')),
                f"${float(p.get('price', 0)):.2f}"
            ])
        return price_data, None


class TicketSalesService:
    @staticmethod
    def search_available_tickets(dep_station_name, arr_station_name, departure_date):
        # 首先验证车站是否存在
        dep_station = Station.find_one({'station_name': dep_station_name})
        arr_station = Station.find_one({'station_name': arr_station_name})
        if not dep_station or not arr_station:
            return [], "Departure or arrival station not found."

        query = """
        SELECT DISTINCT
            DTS.train_number,
            DTS.departure_date,
            DTS.remaining_seats,
            DS.station_name AS departure_station_name,
            AS_st.station_name AS arrival_station_name,
            P.seat_type,
            P.price
        FROM
            DailyTrainStatus DTS
        JOIN
            Trains T ON DTS.train_number = T.train_number
        JOIN
            Prices P ON T.train_number = P.train_number
        JOIN
            Stations DS ON P.departure_station_id = DS.station_id
        JOIN
            Stations AS_st ON P.arrival_station_id = AS_st.station_id
        WHERE
            DTS.remaining_seats > 0
            AND DTS.departure_date = %s
            AND EXISTS (
                SELECT 1 FROM Stopovers S1 
                WHERE S1.train_number = T.train_number 
                AND S1.station_id = %s
            )
            AND EXISTS (
                SELECT 1 FROM Stopovers S2 
                WHERE S2.train_number = T.train_number 
                AND S2.station_id = %s
                AND S2.stop_order > (
                    SELECT stop_order FROM Stopovers 
                    WHERE train_number = T.train_number 
                    AND station_id = %s
                    LIMIT 1
                )
            )
        """
        params = (
            departure_date,
            dep_station.station_id,
            arr_station.station_id,
            dep_station.station_id
        )
        
        results = db.execute_query(query, params, fetch_all=True)

        if not results:
            return [], "No tickets found for your criteria."

        ticket_data = []
        for r in results:
            ticket_data.append([
                r['train_number'],
                str(r['departure_date']),
                r['departure_station_name'],
                r['arrival_station_name'],
                r['seat_type'],
                f"${float(r['price']):.2f}",
                r['remaining_seats']
            ])
        return ticket_data, None

    @staticmethod
    def sell_ticket(train_number, departure_date, seat_number, passenger_name,
                   id_type, id_number, dep_station_name, arr_station_name,
                   ticket_price, salesperson_id):
        # 验证列车是否存在
        train = Train.find_one({'train_number': train_number})
        if not train:
            return False, f"Error: Train {train_number} not found."

        # 验证车站是否存在
        dep_station = Station.find_one({'station_name': dep_station_name})
        arr_station = Station.find_one({'station_name': arr_station_name})
        if not dep_station or not arr_station:
            return False, "Departure or arrival station not found for selling ticket."

        # 验证售票员是否存在
        salesperson = Salesperson.find_one({'salesperson_id': salesperson_id})
        if not salesperson:
            return False, "Salesperson not found."

        # 检查座位是否可用
        daily_status = DailyTrainStatus.find_one({
            'train_number': train_number,
            'departure_date': departure_date
        })
        if not daily_status or daily_status['remaining_seats'] <= 0:
            return False, "No seats available for this train on the selected date."

        # 创建订单
        new_order = SalesOrder(
            train_number=train_number,
            departure_date=departure_date,
            seat_number=seat_number,
            passenger_name=passenger_name,
            id_type=id_type,
            id_number=id_number,
            departure_station_id=dep_station.station_id,
            arrival_station_id=arr_station.station_id,
            ticket_price=ticket_price,
            salesperson_id=salesperson_id,
            sales_time=datetime.datetime.now(),
            order_status='Confirmed'
        )
        
        if new_order.save():
            # 更新剩余座位数
            updated_seats = daily_status['remaining_seats'] - 1
            DailyTrainStatus(
                train_number=train_number,
                departure_date=departure_date,
                remaining_seats=updated_seats
            ).save()
            
            return True, f"Ticket sold successfully! Order ID: {new_order.order_id}"
        return False, "Failed to sell ticket. Check availability or data."

    @staticmethod
    def refund_ticket(order_id, refund_amount, salesperson_id):
        # 验证订单是否存在
        order = SalesOrder.find_one({'order_id': order_id})
        if not order:
            return False, f"Order ID {order_id} not found."
            
        # 检查订单状态
        if order.get('order_status') == 'Refunded':
            return False, f"Order ID {order_id} has already been refunded."

        # 验证售票员是否存在
        salesperson = Salesperson.find_one({'salesperson_id': salesperson_id})
        if not salesperson:
            return False, "Salesperson not found."

        # 创建退款记录
        new_refund = Refund(
            order_id=order_id,
            refund_amount=refund_amount,
            salesperson_id=salesperson_id,
            refund_time=datetime.datetime.now()
        )
        
        if new_refund.save():
            # 更新订单状态为已退款
            order_obj = SalesOrder(**order)
            order_obj.order_status = 'Refunded'
            order_obj.save()
            
            # 更新剩余座位数
            daily_status = DailyTrainStatus.find_one({
                'train_number': order['train_number'],
                'departure_date': order['departure_date']
            })
            if daily_status:
                updated_seats = daily_status['remaining_seats'] + 1
                DailyTrainStatus(
                    train_number=order['train_number'],
                    departure_date=order['departure_date'],
                    remaining_seats=updated_seats
                ).save()
            
            return True, f"Ticket for Order ID {order_id} refunded successfully."
        return False, "Failed to refund ticket."

    @staticmethod
    def get_train_sales_summary(train_number, departure_date):
        query = "CALL GetTrainSalesSummary(%s, %s)"
        result = db.execute_query(query, (train_number, departure_date), fetch_one=True)
        if not result:
            return None, f"No sales data found for Train {train_number} on {departure_date}."

        summary_data = [
            ["Total Tickets Sold", result.get('total_tickets_sold', 0)],
            ["Total Sales Amount", f"${float(result.get('total_sales_amount', 0.00)):.2f}"]
        ]
        return summary_data, None

    @staticmethod
    def get_salesperson_daily_revenue(sales_date):
        query = "CALL GetSalespersonDailyRevenue(%s)"
        results = db.execute_query(query, (sales_date,), fetch_all=True)
        if not results:
            return [], f"No revenue data found for {sales_date}."

        revenue_data = []
        for r in results:
            revenue_data.append([
                r['salesperson_id'],
                r['salesperson_name'],
                f"${float(r['total_revenue']):.2f}"
            ])
        return revenue_data, None