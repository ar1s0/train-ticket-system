import mysql.connector
from datetime import datetime

# 不包含数据库名的配置
DB_CONFIG_NO_DB = {
    'host': 'localhost',
    'user': 'root',
    'password': '123456',
    'port': 3306
}

# 包含数据库名的完整配置
DB_CONFIG = {
    **DB_CONFIG_NO_DB,
    'database': 'date_test'
}

s = '2024-05-25 09:30:00'
print(type(s))
dt = datetime.strptime(s, '%Y-%m-%d %H:%M:%S')
print(dt)

try:
    # 首先创建数据库（如果不存在）
    conn = mysql.connector.connect(**DB_CONFIG_NO_DB)
    cursor = conn.cursor()
    
    # 创建数据库
    create_db_query = "CREATE DATABASE IF NOT EXISTS date_test"
    cursor.execute(create_db_query)
    print("数据库 date_test 已创建（如果不存在）")
    cursor.close()
    conn.close()
    
    # 使用包含数据库名的配置重新连接
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    # 检查表是否存在
    check_table_query = """
    SELECT COUNT(*)
    FROM information_schema.tables
    WHERE table_schema = %s
    AND table_name = 'date_test'
    """
    cursor.execute(check_table_query, (DB_CONFIG['database'],))
    table_exists = cursor.fetchone()[0]
    
    if not table_exists:
        # 创建表
        create_table_query = """
        CREATE TABLE date_test (
            id INT AUTO_INCREMENT PRIMARY KEY,
            event_date DATETIME
        )
        """
        cursor.execute(create_table_query)
        print("表 date_test 已创建")
    
    # 准备插入语句
    insert_query = "INSERT INTO date_test (event_date) VALUES (%s)"
    
    # 使用之前解析的datetime对象
    cursor.execute(insert_query, (dt,))
    
    # 提交事务
    conn.commit()
    print("日期插入成功！")

except mysql.connector.Error as err:
    print(f"数据库错误: {err}")

finally:
    # 关闭连接
    if 'cursor' in locals():
        cursor.close()
    if 'conn' in locals():
        conn.close()