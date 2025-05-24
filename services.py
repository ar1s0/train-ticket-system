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
            departure_station_id=dep_station['station_id'],
            arrival_station_id=arr_station['station_id']
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
    def list_all_trains():
        trains = Train.find_all()
        if not trains:
            return [], "No trains found."

        train_data = []
        for t in trains:
            dep_station = Station.find_one({'station_id': t['departure_station_id']})
            arr_station = Station.find_one({'station_id': t['arrival_station_id']})
            train_data.append([
                t['train_number'],
                t['train_type'],
                t['total_seats'],
                dep_station['station_name'],
                arr_station['station_name']
            ])
        return train_data, None

class StationService:
    @staticmethod
    def add_station(station_name, station_code=None):
        new_station = Station(station_name=station_name, station_code=station_code)
        if new_station.save():
            return True, f"Station '{station_name}' added successfully."
        return False, f"Failed to add station '{station_name}'. It might already exist."

    @staticmethod
    def list_all_stations():
        stations = Station.find_all()
        if not stations:
            return [], "No stations found."

        station_data = []
        for s in stations:
            station_data.append([
                s['station_id'],
                s['station_name'],
                s['station_code'] if s['station_code'] else 'N/A'
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

        new_price = Price(
            train_number=train_number,
            departure_station_id=dep_station['station_id'],
            arrival_station_id=arr_station['station_id'],
            seat_type=seat_type,
            price=price_amount
        )
        if new_price.save():
            return True, f"Price for {train_number} ({dep_station_name}-{arr_station_name}, {seat_type}) added successfully."
        return False, "Failed to add price rule. It might already exist."

    @staticmethod
    def list_prices_for_train(train_number):
        prices = Price.find_all({'train_number': train_number})
        if not prices:
            return [], f"No prices found for train {train_number}."

        price_data = []
        for p in prices:
            dep_station = Station.find_one({'station_id': p['departure_station_id']})
            arr_station = Station.find_one({'station_id': p['arrival_station_id']})
            price_data.append([
                dep_station['station_name'],
                arr_station['station_name'],
                p['seat_type'],
                f"${float(p['price']):.2f}"
            ])
        return price_data, None

class TicketSalesService:
    @staticmethod
    def search_available_tickets(dep_station_name, arr_station_name, departure_date):
        query = """
        SELECT
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
            Stations DS ON T.departure_station_id = DS.station_id
        JOIN
            Stations AS_st ON T.arrival_station_id = AS_st.station_id
        JOIN
            Prices P ON T.train_number = P.train_number AND P.departure_station_id = DS.station_id AND P.arrival_station_id = AS_st.station_id
        WHERE
            DTS.remaining_seats > 0
            AND DTS.departure_date = %s
            AND DS.station_name = %s
            AND AS_st.station_name = %s
        """
        params = (departure_date, dep_station_name, arr_station_name)
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
        train_data = Train.find_one({'train_number': train_number})
        if not train_data:
            return False, f"Error: Train {train_number} not found."

        dep_station = Station.find_one({'station_name': dep_station_name})
        arr_station = Station.find_one({'station_name': arr_station_name})
        if not dep_station or not arr_station:
            return False, "Departure or arrival station not found for selling ticket."

        new_order = SalesOrder(
            train_number=train_number,
            departure_date=departure_date,
            seat_number=seat_number,
            passenger_name=passenger_name,
            id_type=id_type,
            id_number=id_number,
            departure_station_id=dep_station['station_id'],
            arrival_station_id=arr_station['station_id'],
            ticket_price=ticket_price,
            salesperson_id=salesperson_id,
            sales_time=datetime.datetime.now()
        )
        if new_order.save():
            return True, f"Ticket sold successfully! Order ID: {new_order.order_id}"
        return False, "Failed to sell ticket. Check availability or data."

    @staticmethod
    def refund_ticket(order_id, refund_amount, salesperson_id):
        order = SalesOrder.find_one({'order_id': order_id})
        if not order:
            return False, f"Order ID {order_id} not found."
        if order['order_status'] == 'Refunded':
            return False, f"Order ID {order_id} has already been refunded."

        new_refund = Refund(
            order_id=order_id,
            refund_amount=refund_amount,
            salesperson_id=salesperson_id,
            refund_time=datetime.datetime.now()
        )
        if new_refund.save():
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