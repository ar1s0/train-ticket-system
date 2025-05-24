# models.py

from database import db
import uuid
import datetime

class BaseModel:
    """Base class for common CRUD operations."""
    _table_name = None
    _primary_key = None

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    @classmethod
    def find_all(cls, conditions=None):
        query = f"SELECT * FROM `{cls._table_name}`"
        params = None
        if conditions:
            where_clauses = [f"`{k}` = %s" for k in conditions.keys()]
            query += " WHERE " + " AND ".join(where_clauses)
            params = tuple(conditions.values())
        return db.execute_query(query, params, fetch_all=True)

    @classmethod
    def find_one(cls, conditions):
        query = f"SELECT * FROM `{cls._table_name}` WHERE "
        where_clauses = [f"`{k}` = %s" for k in conditions.keys()]
        query += " AND ".join(where_clauses)
        params = tuple(conditions.values())
        return db.execute_query(query, params, fetch_one=True)

    def save(self):
        # Determine if it's an insert or update
        if hasattr(self, self._primary_key) and getattr(self, self._primary_key) is not None:
            # Update existing record
            updates = []
            params = []
            for k, v in self.__dict__.items():
                if k != self._primary_key and k != "_table_name" and k != "_primary_key":
                    updates.append(f"`{k}` = %s")
                    params.append(v)
            query = f"UPDATE `{self._table_name}` SET {', '.join(updates)} WHERE `{self._primary_key}` = %s"
            params.append(getattr(self, self._primary_key))
            return db.execute_query(query, tuple(params))
        else:
            # Insert new record
            columns = []
            values = []
            for k, v in self.__dict__.items():
                if k != "_table_name" and k != "_primary_key":
                    columns.append(f"`{k}`")
                    values.append(v)
            placeholders = ", ".join(["%s"] * len(columns))
            query = f"INSERT INTO `{self._table_name}` ({', '.join(columns)}) VALUES ({placeholders})"
            return db.execute_query(query, tuple(values))

    @classmethod
    def delete(cls, conditions):
        query = f"DELETE FROM `{cls._table_name}` WHERE "
        where_clauses = [f"`{k}` = %s" for k in conditions.keys()]
        query += " AND ".join(where_clauses)
        params = tuple(conditions.values())
        return db.execute_query(query, params)


class Station(BaseModel):
    _table_name = "Stations"
    _primary_key = "station_id"

    def __init__(self, station_id=None, station_name=None, station_code=None):
        super().__init__(station_id=station_id, station_name=station_name, station_code=station_code)

class Train(BaseModel):
    _table_name = "Trains"
    _primary_key = "train_number"

    def __init__(self, train_number=None, train_type=None, total_seats=None,
                 departure_station_id=None, arrival_station_id=None):
        super().__init__(
            train_number=train_number, train_type=train_type, total_seats=total_seats,
            departure_station_id=departure_station_id, arrival_station_id=arrival_station_id
        )

class Stopover(BaseModel):
    _table_name = "Stopovers"
    _primary_key = "stopover_id"

    def __init__(self, stopover_id=None, train_number=None, station_id=None,
                 arrival_time=None, departure_time=None, stop_order=None):
        super().__init__(
            stopover_id=stopover_id, train_number=train_number, station_id=station_id,
            arrival_time=arrival_time, departure_time=departure_time, stop_order=stop_order
        )

class Price(BaseModel):
    _table_name = "Prices"
    _primary_key = "price_id"

    def __init__(self, price_id=None, train_number=None, departure_station_id=None,
                 arrival_station_id=None, seat_type=None, price=None):
        super().__init__(
            price_id=price_id, train_number=train_number, departure_station_id=departure_station_id,
            arrival_station_id=arrival_station_id, seat_type=seat_type, price=price
        )

class Salesperson(BaseModel):
    _table_name = "Salespersons"
    _primary_key = "salesperson_id"

    def __init__(self, salesperson_id=None, salesperson_name=None, contact_number=None,
                 email=None, password_hash=None, role=None):
        super().__init__(
            salesperson_id=salesperson_id, salesperson_name=salesperson_name, contact_number=contact_number,
            email=email, password_hash=password_hash, role=role
        )

class DailyTrainStatus(BaseModel):
    _table_name = "DailyTrainStatus"
    _primary_key = ["train_number", "departure_date"] # Composite primary key

    def __init__(self, train_number=None, departure_date=None, remaining_seats=None):
        super().__init__(
            train_number=train_number, departure_date=departure_date, remaining_seats=remaining_seats
        )

    def save(self):
        # Override save for composite primary key
        if self.train_number and self.departure_date:
            # Try to update first
            updates = []
            params = []
            for k, v in self.__dict__.items():
                if k not in self._primary_key and k != "_table_name" and k != "_primary_key":
                    updates.append(f"`{k}` = %s")
                    params.append(v)

            if updates:
                query = f"UPDATE `{self._table_name}` SET {', '.join(updates)} WHERE `train_number` = %s AND `departure_date` = %s"
                params.extend([self.train_number, self.departure_date])
                row_count = db.execute_query(query, tuple(params))
                if row_count > 0:
                    return row_count

            # If no update or update failed, insert
            columns = []
            values = []
            for k, v in self.__dict__.items():
                if k != "_table_name" and k != "_primary_key":
                    columns.append(f"`{k}`")
                    values.append(v)
            placeholders = ", ".join(["%s"] * len(columns))
            query = f"INSERT INTO `{self._table_name}` ({', '.join(columns)}) VALUES ({placeholders})"
            return db.execute_query(query, tuple(values))
        return None

class SalesOrder(BaseModel):
    _table_name = "SalesOrders"
    _primary_key = "order_id"

    def __init__(self, order_id=None, train_number=None, departure_date=None,
                 seat_number=None, passenger_name=None, id_type=None,
                 id_number=None, departure_station_id=None, arrival_station_id=None,
                 ticket_price=None, sales_time=None, salesperson_id=None,
                 order_status=None):
        super().__init__(
            order_id=order_id, train_number=train_number, departure_date=departure_date,
            seat_number=seat_number, passenger_name=passenger_name, id_type=id_type,
            id_number=id_number, departure_station_id=departure_station_id,
            arrival_station_id=arrival_station_id, ticket_price=ticket_price,
            sales_time=sales_time, salesperson_id=salesperson_id,
            order_status=order_status
        )
        if self.order_id is None:
            self.order_id = str(uuid.uuid4()) # Generate a UUID for the order_id

class Refund(BaseModel):
    _table_name = "Refunds"
    _primary_key = "refund_id"

    def __init__(self, refund_id=None, order_id=None, refund_time=None,
                 refund_amount=None, salesperson_id=None):
        super().__init__(
            refund_id=refund_id, order_id=order_id, refund_time=refund_time,
            refund_amount=refund_amount, salesperson_id=salesperson_id
        )
        if self.refund_id is None:
            self.refund_id = str(uuid.uuid4()) # Generate a UUID for the refund_id