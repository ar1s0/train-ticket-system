import tkinter as tk
from tkinter import messagebox, simpledialog, Toplevel, Label, Entry, Button
from tkinter import ttk
import datetime
import threading
import os
import json
from queue import Queue

from services import TrainService, StationService, PriceService, TicketService, OrderService, SalespersonService
from database import db 
from db_setup import setup_database
from db_maintenance import backup_database, restore_database, delete_backup

main_window = None  # To hold the reference to the main Tkinter window

# --- Helper Functions ---
def clear_frame(frame):
    """Destroys all widgets in a frame."""
    for widget in frame.winfo_children():
        widget.destroy()

def create_modal_window(parent, title, geometry="400x300"):
    """创建模态子窗口的通用函数"""
    window = Toplevel(parent)
    window.withdraw() # Hide the window initially
    window.title(title)
    window.geometry(geometry)
    window.transient(parent)  # 设置为父窗口的子窗口
    window.grab_set()  # 设置为模态窗口
    
    # Center the window
    window.update_idletasks()
    center_window(window)
    
    # Show the window
    window.deiconify()
    
    return window

def show_message(title, message):
    """信息消息窗口"""
    message_window = create_modal_window(
        main_window,
        title,
        "300x150"
    )

    Label(message_window, text=message, wraplength=250).pack(pady=20)
    Button(message_window, text="OK", 
           command=message_window.destroy).pack(pady=10)

def show_error(title, message):
    """错误消息窗口"""
    error_window = create_modal_window(
        main_window,
        title,
        "300x150"
    )

    Label(error_window, text=message, wraplength=250).pack(pady=20)
    Button(error_window, text="OK", 
           command=error_window.destroy).pack(pady=10)

def show_confirmation(title, message):
    """确认对话框"""
    confirm_window = create_modal_window(
        main_window,
        title,
        "300x150"
    )

    result = [False]  # 使用列表存储结果，以便在内部函数中修改
    
    def on_yes():
        result[0] = True
        confirm_window.destroy()
        
    def on_no():
        result[0] = False
        confirm_window.destroy()
    
    Label(confirm_window, text=message, wraplength=250).pack(pady=20)
    
    button_frame = tk.Frame(confirm_window)
    button_frame.pack(pady=10)
    
    Button(button_frame, text="Yes", command=on_yes).pack(side=tk.LEFT, padx=10)
    Button(button_frame, text="No", command=on_no).pack(side=tk.LEFT, padx=10)
    
    confirm_window.wait_window()  # 等待窗口关闭
    return result[0]

def create_booking_window(train_info):
    """创建订票窗口"""
    booking_window = create_modal_window(
        main_window,
        "Book Ticket",
        "400x300"
    )
    
    # 显示选中的车次信息
    Label(booking_window, text=f"Train: {train_info[0]}", font=("Arial", 12)).pack(pady=5)
    Label(booking_window, text=f"From: {train_info[1]} -> To: {train_info[3]}", font=("Arial", 12)).pack(pady=5)
    Label(booking_window, text=f"Price: ¥{train_info[5]}", font=("Arial", 12)).pack(pady=5)
    
    # 输入客户信息
    Label(booking_window, text="Name:").pack(pady=5)
    name_entry = Entry(booking_window)
    name_entry.insert(0, "张三")  # 默认值
    name_entry.pack(pady=5)
    
    Label(booking_window, text="ID Card:").pack(pady=5)
    id_card_entry = Entry(booking_window)
    id_card_entry.insert(0, "110101199001011234")  # 默认值
    id_card_entry.pack(pady=5)
    
    def confirm_booking():
        name = name_entry.get().strip()
        id_card = id_card_entry.get().strip()
        
        if not name or not id_card:
            show_error("Error", "Please fill in all fields")
            return
            
        success, message = OrderService.create_order(
            train_info[0],  # train_number
            train_info[7],  # train_type
            train_info[1],  # departure_station
            train_info[3],  # arrival_station
            train_info[5],  # price
            name,
            id_card
        )
        
        if success:
            show_message("Success", message)
            booking_window.destroy()
        else:
            show_error("Error", message)
    
    Button(booking_window, text="Confirm Booking", 
           command=confirm_booking).pack(pady=20)
    Button(booking_window, text="Cancel", 
           command=booking_window.destroy).pack(pady=5)

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

    if enable_booking:
        selected_train_info = None  # 添加变量存储选中的车次信息
        
        def on_select(event):
            nonlocal selected_train_info
            selected_items = tree.selection()
            if not selected_items:
                return
            item = selected_items[0]
            selected_train_info = tree.item(item)['values']
        
        def on_book():
            if not selected_train_info:
                messagebox.showwarning("Warning", "Please select a train first")
                return
            create_booking_window(selected_train_info)
        
        tree.bind('<<TreeviewSelect>>', on_select)
        
        # 替换原来的提示标签，添加订票按钮
        booking_frame = tk.Frame(data_window)
        booking_frame.grid(row=2, column=0, pady=5)
        
        Label(booking_frame, text="Select a train and click Book to proceed", 
              font=("Arial", 10, "italic")).pack(side=tk.LEFT, padx=5)
        Button(booking_frame, text="Book Selected Train", 
               command=on_book).pack(side=tk.LEFT, padx=5)
        
        # 调整其他按钮的位置
        Button(data_window, text="Close", 
               command=data_window.destroy).grid(row=3, column=0, pady=5)

    # 添加订单操作按钮
    if is_order_view:
        def on_select(event):
            selected_items = tree.selection()
            if not selected_items:
                return
            item = selected_items[0]
            values = tree.item(item)['values']
            order_status = values[-1]  # status是最后一列
            cancel_btn['state'] = 'normal' if order_status == 'Ready' else 'disabled'
            refund_btn['state'] = 'normal' if order_status == 'Success' else 'disabled'

        def cancel_order():
            selected_items = tree.selection()
            if not selected_items:
                messagebox.showwarning("Warning", "Please select an order first")
                return
            item = selected_items[0]
            order_id = tree.item(item)['values'][0]
            
            if show_confirmation("Confirm Cancel", "Are you sure you want to cancel this order?"):
                success, message = OrderService.cancel_order(order_id)
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

        def request_refund():
            selected_items = tree.selection()
            if not selected_items:
                messagebox.showwarning("Warning", "Please select an order first")
                return
            item = selected_items[0]
            order_id = tree.item(item)['values'][0]
            
            if show_confirmation("Confirm Refund", "Are you sure you want to request a refund for this order?"):
                success, message = OrderService.request_refund(order_id)
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
        
        cancel_btn = Button(action_frame, text="Cancel Order", state='disabled', command=cancel_order)
        cancel_btn.pack(side=tk.LEFT, padx=5)
        
        refund_btn = Button(action_frame, text="Request Refund", state='disabled', command=request_refund)
        refund_btn.pack(side=tk.LEFT, padx=5)

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

def center_window(window):
    """将窗口居中显示"""
    window.update_idletasks()  # 更新窗口大小信息
    width = window.winfo_width()
    height = window.winfo_height()
    x = (window.winfo_screenwidth() // 2) - (width // 2)
    y = (window.winfo_screenheight() // 2) - (height // 2)
    window.geometry('{}x{}+{}+{}'.format(width, height, x, y))

def validate_date(date_str):
    """验证日期格式是否正确
    
    Args:
        date_str (str): 日期字符串，格式应为 YYYY-MM-DD
        
    Returns:
        bool: 日期格式是否有效
    """
    if not date_str:  # 允许为空
        return True
        
    try:
        datetime.datetime.strptime(date_str, '%Y-%m-%d')
        return True
    except ValueError:
        return False

# --- Menu Frames ---
def show_search_trains_frame():
    clear_frame(main_window)
    Label(main_window, text="Search Trains", font=("Arial", 14)).pack(pady=10)

    # 出发站
    Label(main_window, text="Departure Station:").pack()
    dep_station_entry = Entry(main_window)
    dep_station_entry.insert(0, "郑州")
    dep_station_entry.pack(pady=5)

    # 到达站
    Label(main_window, text="Arrival Station:").pack()
    arr_station_entry = Entry(main_window)
    arr_station_entry.insert(0, "武汉")
    arr_station_entry.pack(pady=5)

    # 出发日期
    Label(main_window, text="Departure Date (YYYY-MM-DD):").pack()
    date_entry = Entry(main_window)
    # date_entry.insert(0, datetime.datetime.now().strftime("%Y-%m-%d"))
    date_entry.pack(pady=5)
    
    def search_trains():
        dep_station = dep_station_entry.get()
        arr_station = arr_station_entry.get()
        departure_date = date_entry.get()

                # 验证日期格式
        if not validate_date(departure_date):
            show_error("Error", "Invalid date format. Please use YYYY-MM-DD format")
            return
        
        display_table(
            lambda: TicketService.search_available_tickets(
                dep_station, arr_station, departure_date
            ),
            ["Train No", "From", "Departure Time", "To", "Arrival Time", 
             "Price", "Seats", "Type"],
            enable_booking=True  # 启用订票功能
        )

    Button(main_window, text="Search", 
           command=search_trains).pack(pady=10)

    Button(main_window, text="Back to Main Menu", 
           command=show_main_menu_frame).pack(pady=20)

def show_main_menu_frame():
    global main_window
    clear_frame(main_window)
    main_window.title("Train Station Management System")

    Label(main_window, text="Station Management Menu", font=("Arial", 16)).pack(pady=20)

    # 添加搜索列车按钮
    Button(main_window, text="Search Trains", 
           command=show_search_trains_frame, width=30).pack(pady=5)

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

    Button(main_window, text="View Price Information", 
           command=show_price_info_frame, width=30).pack(pady=5)
           
    Button(main_window, text="Query My Orders", 
           command=show_order_query_frame, width=30).pack(pady=5)

    Button(main_window, text="Staff Operations", 
           command=show_staff_orders_frame, width=30).pack(pady=5)

    # 添加新按钮：查看乘务员工作情况
    Button(main_window, text="View Staff Performance", 
           command=lambda: show_staff_login_for_report(), width=30).pack(pady=5)

    # Add database maintenance button (before Exit button)
    Button(main_window, text="Database Maintenance", 
           command=show_database_maintenance_frame, width=30).pack(pady=5)

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
            ["Train", "Station", "Code", "Arrival", "Departure", 
             "Type", "Order", "Sold_tickets"]
        )
    
    Button(main_window, text="Query Route", 
           command=query_route).pack(pady=10)
    
    Button(main_window, text="Back to Main Menu", 
           command=show_main_menu_frame).pack(pady=20)

def show_price_info_frame():
    clear_frame(main_window)
    Label(main_window, text="Price Information", font=("Arial", 14)).pack(pady=10)

    Label(main_window, text="Train Number:").pack()
    train_num_entry = Entry(main_window)
    train_num_entry.insert(0, "G1")
    train_num_entry.pack()
    
    Button(main_window, text="List Prices", 
           command=lambda: display_table(
               lambda: PriceService.list_prices_for_train(train_num_entry.get()),
               ["Departure", "Arrival", "Price"]
           )).pack(pady=5)

    Button(main_window, text="Back to Main Menu", command=show_main_menu_frame).pack(pady=20)

def show_order_query_frame():
    clear_frame(main_window)
    Label(main_window, text="Query Orders", font=("Arial", 14)).pack(pady=10)

    # Name input
    Label(main_window, text="Name:").pack()
    name_entry = Entry(main_window)
    name_entry.insert(0, "张三")  # Default value
    name_entry.pack(pady=5)

    # ID Card input
    Label(main_window, text="Phone:").pack()
    phone_entry = Entry(main_window)
    phone_entry.insert(0, "13800138000")  # Default value
    phone_entry.pack(pady=5)
    
    def query_orders():
        name = name_entry.get().strip()
        id_card = phone_entry.get().strip()
        
        if not name or not id_card:
            show_error("Error", "Please fill in all fields")
            return
            
        display_table(
            lambda: OrderService.get_orders_by_passenger(name, id_card),
            ["order_id", "train_number", "train_type", "From", "To", 
             "Price", "customer_name", "customer_phone", "operation_type", 
             "operation_time", "status"],
            is_order_view=True  # 标记为订单视图
        )

    Button(main_window, text="Query", 
           command=query_orders).pack(pady=10)

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

def show_database_maintenance_frame():
    """显示数据库维护界面"""
    def verify_manager():
        login_window = create_modal_window(
            main_window,
            "Manager Authentication",
            "300x200"
        )
        
        Label(login_window, text="Manager Login Required", 
              font=("Arial", 12)).pack(pady=10)
        
        Label(login_window, text="Manager ID:").pack()
        id_entry = Entry(login_window)
        id_entry.insert(0, "SP001")  # 默认值
        id_entry.pack(pady=5)
        
        Label(login_window, text="Password:").pack()
        password_entry = Entry(login_window, show="*")
        password_entry.insert(0, "1")  # 默认值
        password_entry.pack(pady=5)
        
        def on_verify():
            staff_id = id_entry.get().strip()
            password = password_entry.get().strip()
            
            success, result = SalespersonService.verify_credentials(staff_id, password)
            
            if success and result.get('role') == 'Manager':
                login_window.destroy()
                show_maintenance_options()
            else:
                show_error("Access Denied", "Only managers can access database maintenance")
                login_window.destroy()
        
        Button(login_window, text="Verify", 
               command=on_verify).pack(pady=10)
        Button(login_window, text="Cancel", 
               command=login_window.destroy).pack(pady=5)

    # 直接调用验证函数
    verify_manager()

    def show_maintenance_options():
        maintenance_window = create_modal_window(
            main_window,
            "Database Maintenance",
            "600x400"
        )
        
        # 创建框架来组织界面
        top_frame = ttk.Frame(maintenance_window)
        top_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # 创建Treeview来显示备份列表
        columns = ("Database", "Created", "Type", "Description")
        backup_tree = ttk.Treeview(maintenance_window, columns=columns, show="headings")
        
        # 设置列标题
        for col in columns:
            backup_tree.heading(col, text=col)
            backup_tree.column(col, width=100)
        
        backup_tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        def list_backups():
            """列出所有备份信息，从本地JSON文件读取，按时间戳倒序排序"""
            backups = []
            backup_dir = "backups"
            history_file = os.path.join(backup_dir, "backup_history.json")
            
            # 确保目录存在
            if not os.path.exists(backup_dir):
                os.makedirs(backup_dir)
                return backups
                
            # 读取备份历史记录
            if os.path.exists(history_file):
                try:
                    with open(history_file, 'r') as f:
                        history = json.load(f)
                        
                    # 格式化每个备份的信息并添加原始时间戳用于排序
                    for backup in history:
                        timestamp = backup.get('timestamp', '')
                        backups.append({
                            'database': backup.get('database', ''),
                            'created': datetime.datetime.fromisoformat(
                                timestamp
                            ).strftime('%Y-%m-%d %H:%M:%S'),
                            'type': backup.get('type', 'Unknown'),
                            'description': backup.get('description', ''),
                            'raw_timestamp': timestamp  # 添加原始时间戳用于排序
                        })
                    
                    # 按时间戳倒序排序
                    backups.sort(key=lambda x: x['raw_timestamp'], reverse=True)
                    
                    # 移除排序用的临时字段
                    for backup in backups:
                        del backup['raw_timestamp']
                        
                except Exception as e:
                    print(f"Error reading backup history: {e}")
                    
            return backups
                
        
        def refresh_backup_list():
            # 清空现有项目
            for item in backup_tree.get_children():
                backup_tree.delete(item)
                
            # 获取备份列表
            backups = list_backups()
            
            # 读取详细信息
            history_file = os.path.join("backups", "backup_history.json")
            history_data = {}
            if os.path.exists(history_file):
                try:
                    with open(history_file, 'r') as f:
                        history = json.load(f)
                        history_data = {h['database']: h for h in history}
                except:
                    pass
            
            # 插入数据
            for backup in backups:
                db_name = backup['database']
                created = backup['created']
                
                # 获取额外信息
                backup_type = "Unknown"
                description = ""
                if db_name in history_data:
                    backup_type = history_data[db_name].get('type', 'Unknown')
                    description = history_data[db_name].get('description', '')
                    
                backup_tree.insert("", tk.END, values=(db_name, created, backup_type, description))
        
        def create_new_backup():
            backup_info_window = create_modal_window(
                maintenance_window,
                "Backup Information",
                "400x200"
            )
            
            Label(backup_info_window, text="Create New Backup", 
                  font=("Arial", 12)).pack(pady=10)
            
            # 添加备注输入框
            Label(backup_info_window, text="Description:").pack()
            description_entry = Entry(backup_info_window, width=40)
            description_entry.pack(pady=5)
            
            # 添加备份类型选择
            Label(backup_info_window, text="Backup Type:").pack()
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
                progress_window = create_modal_window(
                    maintenance_window,
                    "Backup in Progress",
                    "300x100"
                )
                
                Label(progress_window, text="Creating backup...", 
                      font=("Arial", 12)).pack(pady=20)
                
                def backup_thread():
                    backup_db = backup_database(description=description, 
                                             backup_type=type_value)
                    progress_window.destroy()
                    if backup_db:
                        show_message("Success", 
                                   f"Database backup created:\n{backup_db}")
                        refresh_backup_list()
                    else:
                        show_error("Error", "Failed to create backup")
                
                threading.Thread(target=backup_thread, daemon=True).start()
            
            Button(backup_info_window, text="Start Backup", 
                   command=do_backup).pack(pady=10)
            Button(backup_info_window, text="Cancel", 
                   command=backup_info_window.destroy).pack(pady=5)
        
        def restore_selected_backup():
            selected = backup_tree.selection()
            if not selected:
                show_error("Error", "Please select a backup to restore")
                return
                
            backup_db = backup_tree.item(selected[0])['values'][0]
            
            if show_confirmation("Confirm Restore", 
                                "This will overwrite the current database. Continue?"):
                
                # 创建进度窗口
                progress_window = create_modal_window(
                    maintenance_window,
                    "Restore in Progress",
                    "300x150"
                )
                
                status_label = Label(progress_window, 
                                text="Restoring database...", 
                                font=("Arial", 12))
                status_label.pack(pady=20)
                
                def restore_thread():
                    try:
                        print(f"Restoring database from backup: {backup_db}")
                        success = restore_database(str(backup_db))
                        if success:
                            progress_window.after(0, lambda: show_message("Success", "Database restored successfully"))
                        else:
                            progress_window.after(0, lambda: show_error("Error", "Failed to restore database"))
                    except Exception as e:
                        progress_window.after(0, lambda: show_error("Error", f"Restore failed: {str(e)}"))
                    finally:
                        progress_window.after(0, progress_window.destroy)
        
                # 启动恢复线程
                threading.Thread(target=restore_thread, daemon=True).start()
        
        def delete_selected_backup():
            selected = backup_tree.selection()
            if not selected:
                show_error("Error", "Please select a backup to delete")
                return
                
            backup_db = backup_tree.item(selected[0])['values'][0]
            
            if show_confirmation("Confirm Delete", 
                               f"Delete backup {backup_db}?"):
                if delete_backup(backup_db):
                    show_message("Success", "Backup deleted successfully")
                    refresh_backup_list()
                else:
                    show_error("Error", "Failed to delete backup")
        
        # 添加按钮
        Button(top_frame, text="Create Backup", 
               command=create_new_backup).pack(side=tk.LEFT, padx=5)
        Button(top_frame, text="Restore Selected", 
               command=restore_selected_backup).pack(side=tk.LEFT, padx=5)
        Button(top_frame, text="Delete Selected", 
               command=delete_selected_backup).pack(side=tk.LEFT, padx=5)
        Button(top_frame, text="Refresh", 
               command=refresh_backup_list).pack(side=tk.LEFT, padx=5)
        Button(maintenance_window, text="Close", 
               command=maintenance_window.destroy).pack(pady=10)
        
        # 初始加载备份列表
        refresh_backup_list()

# --- Main Application Logic ---
def run_gui_app():
    global main_window
    main_window = tk.Tk()
    main_window.withdraw() # Hide initially
    
    main_window.title("Train Station Management System")
    main_window.geometry("500x500")
    
    # Attempt to set up the database before anything else
    print("Initializing database setup...")
    if setup_database():
        print("Database initialized successfully!")
    else:
        show_error("Database Setup Failed", "Could not set up the database. Check your MySQL connection and permissions.")
        main_window.destroy()
        return

    
    restore_database("test")

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