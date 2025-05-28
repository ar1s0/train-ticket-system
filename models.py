# models.py

from database import db

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
        params = []
        if conditions:
            where_clauses = []
            for k, v in conditions.items():
                if v is not None:
                    where_clauses.append(f"`{k}` = %s")
                    params.append(v)
            if where_clauses:
                query += " WHERE " + " AND ".join(where_clauses)
        return db.execute_query(query, tuple(params) if params else None, fetch_all=True)

    @classmethod
    def find_one(cls, conditions):
        if not conditions:
            return None
            
        where_clauses = []
        params = []
        for k, v in conditions.items():
            if v is not None:
                where_clauses.append(f"`{k}` = %s")
                params.append(v)
        
        if not where_clauses:
            return None
            
        query = f"SELECT * FROM `{cls._table_name}` WHERE " + " AND ".join(where_clauses)
        return db.execute_query(query, tuple(params), fetch_one=True)

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
        if not conditions:
            return False
            
        where_clauses = []
        params = []
        for k, v in conditions.items():
            if v is not None:
                where_clauses.append(f"`{k}` = %s")
                params.append(v)
        
        if not where_clauses:
            return False
            
        query = f"DELETE FROM `{cls._table_name}` WHERE " + " AND ".join(where_clauses)
        return db.execute_query(query, tuple(params))


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
                 arrival_station_id=None, price=None):
        super().__init__(
            price_id=price_id, train_number=train_number, 
            departure_station_id=departure_station_id,
            arrival_station_id=arrival_station_id, price=price
        )