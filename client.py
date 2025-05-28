import tkinter as tk
from tkinter import messagebox, simpledialog, Toplevel, Label, Entry, Button
from tkinter import ttk
import datetime
from queue import Queue

from services import TrainService, StationService, TicketService, OrderService
from database import db 
from gui_utils import clear_frame, create_modal_window, show_message, show_error, show_confirmation, validate_date, center_window

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
            train_info[8],  # train_type
            train_info[1],  # start_date
            train_info[2],  # departure_station
            train_info[4],  # arrival_station
            train_info[6],  # price
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

# --- Menu Frames ---
def show_search_trains_frame():
    clear_frame(main_window)
    Label(main_window, text="Search Trains", font=("Arial", 14)).pack(pady=10)

    # 出发站
    Label(main_window, text="Departure Station:").pack()
    dep_station_entry = Entry(main_window)
    dep_station_entry.insert(0, "北京")
    dep_station_entry.pack(pady=5)

    # 到达站
    Label(main_window, text="Arrival Station:").pack()
    arr_station_entry = Entry(main_window)
    arr_station_entry.insert(0, "上海")
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
            ["Train No", "Start Date", "From", "Departure Time", "To", "Arrival Time", 
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
    main_window.title("用户界面")

    Label(main_window, text="用户界面", font=("Arial", 16)).pack(pady=20)

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
           
    Button(main_window, text="Query My Orders", 
           command=show_order_query_frame, width=30).pack(pady=5)

    Button(main_window, text="Exit", command=main_window.quit, width=30).pack(pady=5)

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