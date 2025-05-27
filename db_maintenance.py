import os
import datetime
import json
import subprocess
from subprocess import Popen, PIPE
from db_config import DB_CONFIG
from tqdm import tqdm
import time
import tkinter as tk
from tkinter import ttk, messagebox
import threading


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

def restore_database(source_db_name):
    """
    将指定数据库导出为当前配置的数据库
    
    Args:
        source_db_name (str): 源数据库名称
        
    Returns:
        bool: 成功返回True，失败返回False
    """
    try:
        # 1. 检查源数据库是否存在
        print(f"\nVerifying source database: {source_db_name}")
        check_cmd = [
            'mysql',
            f'-h{DB_CONFIG["host"]}',
            f'-P{DB_CONFIG["port"]}',
            f'-u{DB_CONFIG["user"]}',
            f'-p{DB_CONFIG["password"]}',
            '-e',
            f'SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME = "{source_db_name}";'
        ]
        
        check_process = Popen(check_cmd, stdout=PIPE, stderr=PIPE)
        stdout, _ = check_process.communicate(timeout=30)
        
        if not stdout.strip():
            print(f"❌ Source database '{source_db_name}' not found")
            return False

        # 2. 创建或重置目标数据库
        print(f"\nCreating/Resetting database {DB_CONFIG['database']}...")
        reset_cmd = [
            'mysql',
            f'-h{DB_CONFIG["host"]}',
            f'-P{DB_CONFIG["port"]}',
            f'-u{DB_CONFIG["user"]}',
            f'-p{DB_CONFIG["password"]}',
            '-e',
            f'DROP DATABASE IF EXISTS `{DB_CONFIG["database"]}`; CREATE DATABASE `{DB_CONFIG["database"]}`;'
        ]
        
        reset_process = Popen(reset_cmd, stdout=PIPE, stderr=PIPE)
        _, stderr = reset_process.communicate(timeout=60)
        
        if reset_process.returncode != 0:
            print(f"❌ Failed to create database: {stderr.decode()}")
            return False

        # 3. 导出源数据库并导入到目标数据库
        print("\nExporting data to target database...")
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
            '--quick',
            '--compress',
            '--max_allowed_packet=512M',
            source_db_name
        ]
        
        restore_cmd = [
            'mysql',
            f'-h{DB_CONFIG["host"]}',
            f'-P{DB_CONFIG["port"]}',
            f'-u{DB_CONFIG["user"]}',
            f'-p{DB_CONFIG["password"]}',
            '--max_allowed_packet=512M',
            '--net_buffer_length=32768',
            '--default-character-set=utf8',
            DB_CONFIG["database"]
        ]
        
        # 使用管道直接传输数据
        dump_process = Popen(dump_cmd, stdout=PIPE, stderr=PIPE)
        restore_process = Popen(restore_cmd, stdin=dump_process.stdout, stdout=PIPE, stderr=PIPE)
        dump_process.stdout.close()
        
        _, stderr = restore_process.communicate(timeout=300)
        
        if restore_process.returncode == 0:
            print(f"\n✅ Database {source_db_name} successfully exported to {DB_CONFIG['database']}")
            return True
        else:
            print(f"\n❌ Export failed: {stderr.decode()}")
            return False

    except subprocess.TimeoutExpired:
        print("\n⚠️ Operation timed out")
        return False
    except Exception as e:
        print(f"\n❌ Export error: {str(e)}")
        return False
    
class DatabaseMaintenanceUI:
    def __init__(self):
        # Create main window
        self.root = tk.Tk()
        self.root.title("Database Maintenance")
        self.root.geometry("600x400")
        self.backup_tree = None
        
        # Center window
        self.center_window()
        
    def center_window(self):
        """将窗口居中显示"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry('{}x{}+{}+{}'.format(width, height, x, y))

    def create_modal_window(self, title, geometry="400x300"):
        """创建模态子窗口"""
        window = tk.Toplevel(self.root)
        window.withdraw()
        window.title(title)
        window.geometry(geometry)
        window.transient(self.root)
        window.grab_set()
        
        # Center window
        window.update_idletasks()
        width = window.winfo_width()
        height = window.winfo_height()
        x = (window.winfo_screenwidth() // 2) - (width // 2)
        y = (window.winfo_screenheight() // 2) - (height // 2)
        window.geometry('{}x{}+{}+{}'.format(width, height, x, y))
        
        window.deiconify()
        return window

    def run(self):
        """启动应用程序"""
        self.show_maintenance_window()
        self.root.mainloop()

    def show_message(self, title, message):
        """显示消息对话框"""
        messagebox.showinfo(title, message)

    def show_error(self, title, message):
        """显示错误对话框"""
        messagebox.showerror(title, message)

    def show_confirmation(self, title, message):
        """显示确认对话框"""
        return messagebox.askyesno(title, message)

    def show_maintenance_window(self):
        """显示数据库维护主窗口"""
        # 创建顶部框架
        top_frame = ttk.Frame(self.root)
        top_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # 创建备份列表
        columns = ("Database", "Created", "Type", "Description")
        self.backup_tree = ttk.Treeview(self.root, columns=columns, show="headings")
        
        # 设置列标题
        for col in columns:
            self.backup_tree.heading(col, text=col)
            self.backup_tree.column(col, width=100)
        
        self.backup_tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # 添加按钮
        ttk.Button(top_frame, text="Create Backup", 
                  command=self.create_new_backup).pack(side=tk.LEFT, padx=5)
        ttk.Button(top_frame, text="Restore Selected", 
                  command=self.restore_selected_backup).pack(side=tk.LEFT, padx=5)
        ttk.Button(top_frame, text="Delete Selected", 
                  command=self.delete_selected_backup).pack(side=tk.LEFT, padx=5)
        ttk.Button(top_frame, text="Refresh", 
                  command=self.refresh_backup_list).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.root, text="Exit", 
                  command=self.root.quit).pack(pady=10)
        
        # 初始加载备份列表
        self.refresh_backup_list()

    def create_new_backup(self):
        """创建新备份对话框"""
        backup_info_window = self.create_modal_window(
            "Backup Information",
            "400x200"
        )
        
        tk.Label(backup_info_window, text="Create New Backup", 
                font=("Arial", 12)).pack(pady=10)
        
        tk.Label(backup_info_window, text="Description:").pack()
        description_entry = tk.Entry(backup_info_window, width=40)
        description_entry.pack(pady=5)
        
        tk.Label(backup_info_window, text="Backup Type:").pack()
        backup_type = ttk.Combobox(backup_info_window, 
                                 values=["Daily", "Weekly", "Monthly", "Manual"],
                                 state="readonly")
        backup_type.set("Manual")
        backup_type.pack(pady=5)
        
        def do_backup():
            description = description_entry.get().strip()
            type_value = backup_type.get()
            backup_info_window.destroy()
            
            # 显示进度窗口
            progress_window = self.create_modal_window(
                "Backup in Progress",
                "300x100"
            )
            
            tk.Label(progress_window, text="Creating backup...", 
                    font=("Arial", 12)).pack(pady=20)
            
            def backup_thread():
                backup_db = backup_database(description=description, 
                                         backup_type=type_value)
                progress_window.destroy()
                if backup_db:
                    self.show_message("Success", 
                                    f"Database backup created:\n{backup_db}")
                    self.refresh_backup_list()
                else:
                    self.show_error("Error", "Failed to create backup")
            
            threading.Thread(target=backup_thread, daemon=True).start()
        
        ttk.Button(backup_info_window, text="Start Backup", 
                  command=do_backup).pack(pady=10)
        ttk.Button(backup_info_window, text="Cancel", 
                  command=backup_info_window.destroy).pack(pady=5)

    def restore_selected_backup(self):
        """恢复选中的备份"""
        selected = self.backup_tree.selection()
        if not selected:
            self.show_error("Error", "Please select a backup to restore")
            return
            
        backup_db = self.backup_tree.item(selected[0])['values'][0]
        
        if self.show_confirmation("Confirm Restore", 
                                "This will overwrite the current database. Continue?"):
            
            progress_window = self.create_modal_window(
                "Restore in Progress",
                "300x150"
            )
            
            tk.Label(progress_window, text="Restoring database...", 
                    font=("Arial", 12)).pack(pady=20)
            
            def restore_thread():
                try:
                    success = restore_database(str(backup_db))
                    if success:
                        self.show_message("Success", "Database restored successfully")
                    else:
                        self.show_error("Error", "Failed to restore database")
                except Exception as e:
                    self.show_error("Error", f"Restore failed: {str(e)}")
                finally:
                    progress_window.destroy()
    
            threading.Thread(target=restore_thread, daemon=True).start()

    def delete_selected_backup(self):
        """删除选中的备份"""
        selected = self.backup_tree.selection()
        if not selected:
            self.show_error("Error", "Please select a backup to delete")
            return
            
        backup_db = self.backup_tree.item(selected[0])['values'][0]
        
        if self.show_confirmation("Confirm Delete", 
                                f"Delete backup {backup_db}?"):
            if delete_backup(backup_db):
                self.show_message("Success", "Backup deleted successfully")
                self.refresh_backup_list()
            else:
                self.show_error("Error", "Failed to delete backup")

    def list_backups(self):
        """列出所有备份信息"""
        backups = []
        backup_dir = "backups"
        history_file = os.path.join(backup_dir, "backup_history.json")
        
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
            return backups
            
        if os.path.exists(history_file):
            try:
                with open(history_file, 'r') as f:
                    history = json.load(f)
                    
                for backup in history:
                    timestamp = backup.get('timestamp', '')
                    backups.append({
                        'database': backup.get('database', ''),
                        'created': datetime.datetime.fromisoformat(
                            timestamp
                        ).strftime('%Y-%m-%d %H:%M:%S'),
                        'type': backup.get('type', 'Unknown'),
                        'description': backup.get('description', ''),
                        'raw_timestamp': timestamp
                    })
                
                backups.sort(key=lambda x: x['raw_timestamp'], reverse=True)
                
                for backup in backups:
                    del backup['raw_timestamp']
                    
            except Exception as e:
                print(f"Error reading backup history: {e}")
                
        return backups

    def refresh_backup_list(self):
        """刷新备份列表显示"""
        for item in self.backup_tree.get_children():
            self.backup_tree.delete(item)
            
        backups = self.list_backups()
        
        for backup in backups:
            self.backup_tree.insert("", tk.END, values=(
                backup['database'],
                backup['created'],
                backup['type'],
                backup['description']
            ))

def main():
    try:
        # 检查数据库连接
        check_cmd = [
            'mysql',
            f'-h{DB_CONFIG["host"]}',
            f'-P{DB_CONFIG["port"]}',
            f'-u{DB_CONFIG["user"]}',
            f'-p{DB_CONFIG["password"]}',
            '-e',
            'SELECT 1;'
        ]
        
        process = Popen(check_cmd, stdout=PIPE, stderr=PIPE)
        _, stderr = process.communicate(timeout=5)
        
        if process.returncode != 0:
            print("Error: Cannot connect to database.")
            print(f"Details: {stderr.decode()}")
            return
        
        # 启动主程序
        app = DatabaseMaintenanceUI()
        app.run()
        
    except Exception as e:
        print(f"Error starting application: {str(e)}")

if __name__ == "__main__":
    main()