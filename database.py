# database.py

import mysql.connector
from mysql.connector import Error
from db_config import DB_CONFIG

class Database:
    def __init__(self):
        self.connection = None
        self.connect()

    def connect(self):
        try:
            self.connection = mysql.connector.connect(**DB_CONFIG)
            if self.connection.is_connected():
                print("Successfully connected to MySQL database")
        except Error as e:
            print(f"Error connecting to MySQL database: {e}")
            self.connection = None # Ensure connection is None if failed

    def close(self):
        if self.connection and self.connection.is_connected():
            self.connection.close()
            print("MySQL connection closed.")

    def execute_query(self, query, params=None, fetch_one=False, fetch_all=False):
        if not self.connection or not self.connection.is_connected():
            print("Database connection is not active. Reconnecting...")
            self.connect()
            if not self.connection or not self.connection.is_connected():
                print("Failed to establish database connection.")
                return None

        cursor = self.connection.cursor(dictionary=True) # Returns rows as dictionaries
        try:
            cursor.execute(query, params)
            if fetch_one:
                result = cursor.fetchone()
                return result
            elif fetch_all:
                result = cursor.fetchall()
                return result
            else:
                self.connection.commit() # Commit changes for INSERT, UPDATE, DELETE
                return cursor.rowcount # Return number of affected rows
        except Error as e:
            self.connection.rollback() # Rollback on error
            print(f"Database query error: {e}")
            return None
        finally:
            cursor.close()

    def call_proc(self, proc_name, args=()):
        """调用存储过程
        
        Args:
            proc_name (str): 存储过程名称
            args (tuple): 存储过程参数
            
        Returns:
            list: 存储过程的结果集，如果出错则返回None
        """
        if not self.connection or not self.connection.is_connected():
            print("Database connection is not active. Reconnecting...")
            self.connect()
            if not self.connection or not self.connection.is_connected():
                print("Failed to establish database connection.")
                return None

        cursor = self.connection.cursor(dictionary=True)
        try:
            # 调用存储过程
            cursor.callproc(proc_name, args)
            
            # 获取所有结果集
            results = []
            for result in cursor.stored_results():
                results.extend(result.fetchall())
                
            self.connection.commit()
            return results
            
        except Error as e:
            self.connection.rollback()
            print(f"Error calling procedure {proc_name}: {e}")
            return None
        finally:
            cursor.close()

# Global database instance
db = Database()