import tkinter as tk
from tkinter import messagebox, simpledialog, Toplevel, Label, Entry, Button
from tkinter import ttk
import datetime
from queue import Queue

from services import TrainService, StationService, TicketService, OrderService, SalespersonService
from database import db 
from db_setup import setup_database
from db_maintenance import DatabaseMaintenanceUI, restore_database
from gui_utils import clear_frame, create_modal_window, show_message, show_error, show_confirmation, center_window, validate_date

def display_table(get_data_func, columns, enable_booking=False, is_order_view=False, is_staff_view=False, staff_info=None):
    """显示数据表格窗口"""
    data_window = create_modal_window(
        main_window,
        "Data View",
        "800x400"
    )
    
    # 创建Treeview
    tree = ttk.Treeview(data_window)
    tree["columns"] = columns
    tree["show"] = "headings"

    # 配置列
    for col in columns:
        tree.heading(col, text=col)
        tree.column(col, width=100)

    # 添加滚动条
    vsb = ttk.Scrollbar(data_window, orient="vertical", command=tree.yview)
    hsb = ttk.Scrollbar(data_window, orient="horizontal", command=tree.xview)
    tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

    # 放置组件
    tree.grid(row=0, column=0, sticky="nsew")
    vsb.grid(row=0, column=1, sticky="ns")
    hsb.grid(row=1, column=0, sticky="ew")

    # 配置网格权重
    data_window.grid_rowconfigure(0, weight=1)
    data_window.grid_columnconfigure(0, weight=1)

    # 添加双击编辑功能
    def on_double_click(event):
        item = tree.selection()[0]
        column = tree.identify_column(event.x)
        col_num = int(column.replace('#', '')) - 1
        
        # 获取当前值
        current_value = tree.item(item)['values'][col_num]
        
        # 创建Entry控件
        entry = Entry(tree)
        entry.insert(0, current_value)
        
        # 获取单元格的bbox
        bbox = tree.bbox(item, column)
        if not bbox:  # 如果单元格不可见
            return
        
        # 配置Entry的大小和位置
        entry.place(x=bbox[0], y=bbox[1],
                   width=bbox[2], height=bbox[3])
        
        # 设置焦点
        entry.focus_set()
        
        def on_enter(event):
            new_value = entry.get()
            values = list(tree.item(item)['values'])
            values[col_num] = new_value
            tree.item(item, values=values)
            entry.destroy()
        
        def on_escape(event):
            entry.destroy()
        
        entry.bind('<Return>', on_enter)
        entry.bind('<Escape>', on_escape)
        # 当Entry失去焦点时也保存修改
        entry.bind('<FocusOut>', on_enter)

    tree.bind('<Double-1>', on_double_click)

    try:
        data, error = get_data_func()
        
        if error:
            messagebox.showinfo("Information", error)
        
        if data:
            for row in data:
                tree.insert("", "end", values=[str(item) if item is not None else "-" for item in row])
                
    except Exception as e:
        messagebox.showerror("Error", f"An error occurred: {str(e)}")

    Button(data_window, text="Close", command=data_window.destroy).grid(row=3, column=0, pady=5)

    # 添加乘务员操作按钮
    if is_staff_view:
        def on_select(event):
            selected_items = tree.selection()
            if not selected_items:
                return
            item = selected_items[0]
            values = tree.item(item)['values']
            status = values[-1]
            approve_btn['state'] = 'normal' if status in ('Ready', 'RefundPending') else 'disabled'
            reject_btn['state'] = 'normal' if status in ('Ready', 'RefundPending') else 'disabled'

        def process_order(approve=True):
            selected_items = tree.selection()
            if not selected_items:
                messagebox.showwarning("Warning", "Please select an order first")
                return
            item = selected_items[0]
            order_id = tree.item(item)['values'][0]
            status = tree.item(item)['values'][-1]
            
            action = "approve" if approve else "reject"
            if show_confirmation("Confirm Action", 
                               f"Are you sure you want to {action} this order?"):
                success, message = OrderService.process_order(order_id, approve, staff_info['salesperson_id'])
                if success:
                    show_message("Success", message)
                    # 刷新订单列表
                    tree.delete(*tree.get_children())
                    data, _ = get_data_func()
                    if data:
                        for row in data:
                            tree.insert("", "end", values=[str(item) if item is not None else "-" for item in row])
                else:
                    show_error("Error", message)

        tree.bind('<<TreeviewSelect>>', on_select)
        
        # 添加操作按钮框架
        action_frame = tk.Frame(data_window)
        action_frame.grid(row=2, column=0, pady=5)
        
        approve_btn = Button(action_frame, text="Approve", state='disabled', 
                           command=lambda: process_order(True))
        approve_btn.pack(side=tk.LEFT, padx=5)
        
        reject_btn = Button(action_frame, text="Reject", state='disabled', 
                           command=lambda: process_order(False))
        reject_btn.pack(side=tk.LEFT, padx=5)

    Button(data_window, text="Close", command=data_window.destroy).grid(row=3, column=0, pady=5)


def show_main_menu_frame():
    global main_window
    clear_frame(main_window)
    main_window.title("销售员操作界面")

    Label(main_window, text="销售员操作界面", font=("Arial", 16)).pack(pady=20)

    Button(main_window, text="View Train Route", 
           command=show_train_route_frame, width=30).pack(pady=5)

    Button(main_window, text="View Train Information", 
           command=lambda: display_table(
               TrainService.list_all_trains,
               ["Train No", "Type", "Seats", "Departure", "Arrival"]
           ), width=30).pack(pady=5)

    Button(main_window, text="View Station Information", 
           command=lambda: display_table(
               StationService.list_all_stations,
               ["ID", "Name", "Code"]
           ), width=30).pack(pady=5)

    Button(main_window, text="Staff Operations", 
           command=show_staff_orders_frame, width=30).pack(pady=5)

    # 添加新按钮：查看乘务员工作情况
    Button(main_window, text="View Staff Performance", 
           command=lambda: show_staff_login_for_report(), width=30).pack(pady=5)

    Button(main_window, text="Exit", command=main_window.quit, width=30).pack(pady=5)

# 添加新函数用于验证管理员身份
def show_staff_login_for_report():
    """显示管理员登录窗口(查看报表专用)"""
    login_window = create_modal_window(
        main_window,
        "Manager Login",
        "300x200"
    )
    
    Label(login_window, text="Manager Login", font=("Arial", 14)).pack(pady=10)
    
    # 管理员ID输入
    Label(login_window, text="Manager ID:").pack()
    id_entry = Entry(login_window)
    id_entry.insert(0, "SP001")  # 默认值
    id_entry.pack(pady=5)
    
    # 密码输入
    Label(login_window, text="Password:").pack()
    password_entry = Entry(login_window, show="*")
    password_entry.insert(0, "1")  # 默认值
    password_entry.pack(pady=5)
    
    def verify_login():
        staff_id = id_entry.get().strip()
        password = password_entry.get().strip()
        
        if not staff_id or not password:
            show_error("Error", "Please fill in all fields")
            return
            
        success, result = SalespersonService.verify_credentials(staff_id, password)
        
        if success and result.get('role') == 'Manager':
            login_window.destroy()
            show_staff_performance_report()  # 直接显示报表
        else:
            show_error("Login Failed", "Only managers can access this feature")
    
    Button(login_window, text="Login", 
           command=verify_login).pack(pady=10)
    Button(login_window, text="Cancel", 
           command=login_window.destroy).pack(pady=5)

def show_train_route_frame():
    clear_frame(main_window)
    Label(main_window, text="Train Route Query", font=("Arial", 14)).pack(pady=10)
    
    # 列车号输入
    Label(main_window, text="Train Number:").pack()
    train_number_entry = Entry(main_window)
    train_number_entry.insert(0, "G1")
    train_number_entry.pack(pady=5)
    
    # 日期输入（可选）
    Label(main_window, text="Date (YYYY-MM-DD, optional):").pack()
    date_entry = Entry(main_window)
    date_entry.pack(pady=5)
    
    def query_route():
        train_number = train_number_entry.get().strip()
        departure_date = date_entry.get().strip()
        
        if not train_number:
            show_error("Error", "Please enter train number")
            return
        
        # 验证日期格式
        if not validate_date(departure_date):
            show_error("Error", "Invalid date format. Please use YYYY-MM-DD format")
            return
            
        display_table(
            lambda: TrainService.get_train_route(
                train_number, 
                departure_date if departure_date else None
            ),
            ["Train", "Start_date", "Station", "Code", "Arrival", "Departure", 
             "Type", "Order", "Sold_tickets"]
        )
    
    Button(main_window, text="Query Route", 
           command=query_route).pack(pady=10)
    
    Button(main_window, text="Back to Main Menu", 
           command=show_main_menu_frame).pack(pady=20)


def show_staff_orders_frame():
    """显示乘务员操作界面"""
    # 直接显示登录窗口
    show_staff_login()

def show_staff_login():
    """显示乘务员登录窗口"""
    login_window = create_modal_window(
        main_window,
        "Staff Login",
        "300x200"
    )
    
    Label(login_window, text="Staff Login", font=("Arial", 14)).pack(pady=10)
    
    # 乘务员ID输入
    Label(login_window, text="Staff ID:").pack()
    id_entry = Entry(login_window)
    id_entry.insert(0, "SP001")  # 默认值
    id_entry.pack(pady=5)
    
    # 密码输入
    Label(login_window, text="Password:").pack()
    password_entry = Entry(login_window, show="*")
    password_entry.insert(0, "1")  # 默认值
    password_entry.pack(pady=5)
    
    def verify_login():
        staff_id = id_entry.get().strip()
        password = password_entry.get().strip()
        
        if not staff_id or not password:
            show_error("Error", "Please fill in all fields")
            return
            
        success, result = SalespersonService.verify_credentials(staff_id, password)
        
        if success:
            login_window.destroy()
            show_staff_dashboard(result)  # 传入验证成功的乘务员信息
        else:
            show_error("Login Failed", result)
    
    Button(login_window, text="Login", 
           command=verify_login).pack(pady=10)
    Button(login_window, text="Cancel", 
           command=login_window.destroy).pack(pady=5)

def show_staff_dashboard(staff_info):
    """显示乘务员操作界面"""
    clear_frame(main_window)
    Label(main_window, text=f"Welcome, {staff_info['salesperson_name']}", 
          font=("Arial", 14)).pack(pady=10)
    
    if staff_info.get('role') == 'manager':  # 只有管理员可以查看报表
        Button(main_window, text="Staff Performance Report", 
               command=show_staff_performance_report, 
               width=30).pack(pady=5)
    
    Label(main_window, text="Pending Orders", 
          font=("Arial", 12)).pack(pady=5)
    
    def refresh_orders():
        display_table(
            OrderService.get_pending_orders,
            ["Order ID", "Train No", "Type", "From", "To", 
             "Price", "Customer", "Phone", "Operation", 
             "Time", "Status"],
            is_staff_view=True,
            staff_info=staff_info  # 传入乘务员信息
        )
    
    Button(main_window, text="View Pending Orders", 
           command=refresh_orders, width=30).pack(pady=5)
    
    Button(main_window, text="Back to Main Menu", 
           command=show_main_menu_frame, width=30).pack(pady=20)

def show_staff_performance_report():
    """显示业务员工作情况报表"""
    report_window = create_modal_window(main_window, "Staff Performance Report", "300x250")
    Label(report_window, text="Staff Performance Report", font=("Arial", 14)).pack(pady=10)
    
    # 乘务员ID输入
    Label(report_window, text="Staff ID (optional):").pack()
    staff_id_entry = Entry(report_window)
    staff_id_entry.pack(pady=5)
    
    # 日期输入
    Label(report_window, text="Date (YYYY-MM-DD):").pack()
    date_entry = Entry(report_window)
    date_entry.insert(0, datetime.datetime.now().strftime("%Y-%m-%d"))
    date_entry.pack(pady=5)
    
    def view_report():
        staff_id = staff_id_entry.get().strip()
        report_date = date_entry.get().strip()
        
        if not validate_date(report_date):
            show_error("Error", "Invalid date format")
            return
            
        report_window.destroy()
        display_table(
            lambda: SalespersonService.get_daily_sales_report(report_date, staff_id),
            ["Staff ID", "Staff Name", "Total Orders", 
             "Booking Revenue", "Refund Amount"],
            is_staff_view=False
        )
    
    Button(report_window, text="View Report", 
           command=view_report).pack(pady=10)
           
    # 添加帮助提示
    help_text = "Leave Staff ID empty to view all staff performance"
    Label(report_window, text=help_text, 
          font=("Arial", 8, "italic")).pack(pady=5)
          
    Button(report_window, text="Cancel", 
           command=report_window.destroy).pack(pady=5)

# --- Main Application Logic ---
def run_gui_app():
    global main_window
    main_window = tk.Tk()
    main_window.withdraw() # Hide initially
    
    main_window.title("Train Station Management System")
    main_window.geometry("500x500")

    # Start with the main menu
    show_main_menu_frame()
    
    # Center and then show
    center_window(main_window)
    main_window.deiconify()
    
    main_window.protocol("WM_DELETE_WINDOW", on_closing)
    main_window.mainloop()
    db.close()  # Ensure database connection is closed after mainloop exits

def on_closing():
    db.close()  # 关闭数据库连接
    main_window.destroy()

if __name__ == "__main__":
    run_gui_app()