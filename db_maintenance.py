import os
import datetime
import json
import subprocess
from subprocess import Popen, PIPE
from db_config import DB_CONFIG

def backup_database(backup_dir="backups", description="", backup_type="Manual"):
    """
    Backup the database by creating a new database with timestamp
    
    Args:
        backup_dir (str): Directory to store backup meta info
        description (str): Backup description
        backup_type (str): Type of backup (Daily/Weekly/Monthly/Manual)
    
    Returns:
        str: Name of backup database if successful, None if failed
    """
    try:
        # Generate backup database name with timestamp
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_db = f"{DB_CONFIG['database']}_backup_{timestamp}"
        
        # 1. Create new database
        create_cmd = [
            'mysql',
            f'-h{DB_CONFIG["host"]}',
            f'-P{DB_CONFIG["port"]}',
            f'-u{DB_CONFIG["user"]}',
            f'-p{DB_CONFIG["password"]}',
            '-e',
            f'CREATE DATABASE `{backup_db}`;'
        ]
        
        create_process = Popen(create_cmd, stdout=PIPE, stderr=PIPE)
        _, create_stderr = create_process.communicate(timeout=60)
        
        if create_process.returncode != 0:
            print(f"Failed to create backup database: {create_stderr.decode()}")
            return None
            
        # 2. Copy all tables, data, routines, triggers, and events
        dump_cmd = [
            'mysqldump',
            f'-h{DB_CONFIG["host"]}',
            f'-P{DB_CONFIG["port"]}',
            f'-u{DB_CONFIG["user"]}',
            f'-p{DB_CONFIG["password"]}',
            '--routines',
            '--triggers',
            '--events',
            '--single-transaction',
            '--quick',           # 减少内存使用
            '--compress',        # 压缩传输数据
            '--max_allowed_packet=256M',  # 增加包大小
            DB_CONFIG['database']
        ]
        
        restore_cmd = [
            'mysql',
            f'-h{DB_CONFIG["host"]}',
            f'-P{DB_CONFIG["port"]}',
            f'-u{DB_CONFIG["user"]}',
            f'-p{DB_CONFIG["password"]}',
            '--max_allowed_packet=256M',  # 增加包大小
            '--net_buffer_length=1000000',  # 增加网络缓冲区
            backup_db
        ]
        
        # Pipe mysqldump directly to mysql
        dump_process = Popen(dump_cmd, stdout=PIPE, stderr=PIPE)
        restore_process = Popen(restore_cmd, stdin=dump_process.stdout, stdout=PIPE, stderr=PIPE)
        dump_process.stdout.close()  # Allow dump_process to receive a SIGPIPE
        
        # Wait for completion
        _, restore_stderr = restore_process.communicate(timeout=300)
        
        if restore_process.returncode != 0:
            print(f"Failed to copy database: {restore_stderr.decode()}")
            # Cleanup on failure
            cleanup_cmd = [
                'mysql',
                f'-h{DB_CONFIG["host"]}',
                f'-P{DB_CONFIG["port"]}',
                f'-u{DB_CONFIG["user"]}',
                f'-p{DB_CONFIG["password"]}',
                '-e',
                f'DROP DATABASE IF EXISTS `{backup_db}`;'
            ]
            Popen(cleanup_cmd).wait()
            return None
            
        # Save backup info to file with more details
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
            
        backup_info = {
            'timestamp': datetime.datetime.now().isoformat(),
            'database': backup_db,
            'description': description,
            'type': backup_type,
            'size': '0'  # You could add actual size calculation here
        }
            
        # Save in both text and JSON format for better tracking
        with open(os.path.join(backup_dir, "backup_history.txt"), "a") as f:
            f.write(f"{backup_info['timestamp']}: {backup_db}\n")
            f.write(f"Type: {backup_type}\n")
            f.write(f"Description: {description}\n")
            f.write("-" * 50 + "\n")
            
        # Also save as JSON for structured access
        history_json = os.path.join(backup_dir, "backup_history.json")
        try:
            if os.path.exists(history_json):
                with open(history_json, 'r') as f:
                    history = json.load(f)
            else:
                history = []
                
            history.append(backup_info)
            
            with open(history_json, 'w') as f:
                json.dump(history, f, indent=2)
                
        except Exception as e:
            print(f"Warning: Could not save backup history to JSON: {e}")
            
        print(f"Database backup created successfully: {backup_db}")
        return backup_db
            
    except Exception as e:
        print(f"Backup error: {str(e)}")
        return None

def restore_database(backup_db_name):
    """
    从备份数据库恢复数据
    
    Args:
        backup_db_name (str): 备份数据库名称
        
    Returns:
        bool: 成功返回True，失败返回False
    """
    try:
        # 1. 验证备份数据库是否存在
        check_cmd = [
            'mysql',
            f'-h{DB_CONFIG["host"]}',
            f'-P{DB_CONFIG["port"]}',
            f'-u{DB_CONFIG["user"]}',
            f'-p{DB_CONFIG["password"]}',
            '-e',
            f'SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME = "{backup_db_name}";'
        ]
        
        check_process = Popen(check_cmd, stdout=PIPE, stderr=PIPE)
        stdout, _ = check_process.communicate(timeout=60)
        
        if not stdout.strip():
            print(f"Backup database '{backup_db_name}' not found")
            return False
            
        # 2. 删除当前数据库并重新创建
        reset_cmd = [
            'mysql',
            f'-h{DB_CONFIG["host"]}',
            f'-P{DB_CONFIG["port"]}',
            f'-u{DB_CONFIG["user"]}',
            f'-p{DB_CONFIG["password"]}',
            '-e',
            f'DROP DATABASE IF EXISTS {DB_CONFIG["database"]}; CREATE DATABASE {DB_CONFIG["database"]};'
        ]
        
        reset_process = Popen(reset_cmd, stdout=PIPE, stderr=PIPE)
        _, reset_stderr = reset_process.communicate(timeout=60)
        
        if reset_process.returncode != 0:
            print(f"Failed to reset database: {reset_stderr.decode()}")
            return False
            
        # 3. 使用mysqldump导出备份数据库并通过管道导入到目标数据库
        dump_cmd = [
            'mysqldump',
            f'-h{DB_CONFIG["host"]}',
            f'-P{DB_CONFIG["port"]}',
            f'-u{DB_CONFIG["user"]}',
            f'-p{DB_CONFIG["password"]}',
            '--routines',
            '--triggers',
            '--events',
            '--single-transaction',
            '--quick',           # 减少内存使用
            '--compress',        # 压缩传输数据
            '--max_allowed_packet=256M',  # 增加包大小
            backup_db_name
        ]
        
        restore_cmd = [
            'mysql',
            f'-h{DB_CONFIG["host"]}',
            f'-P{DB_CONFIG["port"]}',
            f'-u{DB_CONFIG["user"]}',
            f'-p{DB_CONFIG["password"]}',
            '--max_allowed_packet=256M',  # 增加包大小
            '--net_buffer_length=1000000',  # 增加网络缓冲区
            DB_CONFIG["database"]
        ]
        
        dump_process = Popen(dump_cmd, stdout=PIPE, stderr=PIPE)
        restore_process = Popen(restore_cmd, stdin=dump_process.stdout, stdout=PIPE, stderr=PIPE)
        dump_process.stdout.close()
        
        try:
            _, stderr = restore_process.communicate(timeout=300)
            if restore_process.returncode == 0:
                print(f"Database restored successfully from: {backup_db_name}")
                return True
            else:
                print(f"Restore failed: {stderr.decode()}")
                return False
        except subprocess.TimeoutExpired:
            dump_process.kill()
            restore_process.kill()
            print("Restore operation timed out")
            return False
            
    except Exception as e:
        print(f"Restore error: {str(e)}")
        return False

def delete_backup(backup_db_name):
    """
    删除指定的备份数据库
    
    Args:
        backup_db_name (str): 备份数据库名称
        
    Returns:
        bool: 成功返回True，失败返回False
    """
    try:
        # 1. 验证是否为备份数据库
        if not backup_db_name.startswith(f"{DB_CONFIG['database']}_backup_"):
            print("Invalid backup database name")
            return False
            
        # 2. 删除数据库
        drop_cmd = [
            'mysql',
            f'-h{DB_CONFIG["host"]}',
            f'-P{DB_CONFIG["port"]}',
            f'-u{DB_CONFIG["user"]}',
            f'-p{DB_CONFIG["password"]}',
            '-e',
            f'DROP DATABASE IF EXISTS `{backup_db_name}`;'
        ]
        
        process = Popen(drop_cmd, stdout=PIPE, stderr=PIPE)
        _, stderr = process.communicate(timeout=60)
        
        if process.returncode != 0:
            print(f"Failed to delete backup: {stderr.decode()}")
            return False
            
        # 3. 更新备份历史记录
        backup_dir = "backups"
        history_json = os.path.join(backup_dir, "backup_history.json")
        
        if os.path.exists(history_json):
            with open(history_json, 'r') as f:
                history = json.load(f)
                
            # 移除已删除的备份记录
            history = [h for h in history if h['database'] != backup_db_name]
            
            with open(history_json, 'w') as f:
                json.dump(history, f, indent=2)
        
        print(f"Backup {backup_db_name} deleted successfully")
        return True
        
    except Exception as e:
        print(f"Delete backup error: {str(e)}")
        return False
