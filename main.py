import tkinter as tk
from tkinter import messagebox, simpledialog, Toplevel, Label, Entry, Button
from tkinter import ttk
import datetime

from services import TrainService, StationService, PriceService
from database import db 
from db_setup import setup_database

main_window = None  # To hold the reference to the main Tkinter window

# --- Helper Functions ---
def clear_frame(frame):
    """Destroys all widgets in a frame."""
    for widget in frame.winfo_children():
        widget.destroy()

def show_message(title, message):
    """Helper to display information messages."""
    messagebox.showinfo(title, message)

def show_error(title, message):
    """Helper to display error messages."""
    messagebox.showerror(title, message)

def display_table(get_data_func, columns):
    # 创建新窗口来显示表格数据
    data_window = Toplevel(main_window)
    data_window.title("Data View")
    data_window.geometry("800x400")

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

    try:
        data, error = get_data_func()
        
        if error:
            messagebox.showinfo("Information", error)
        
        if data:
            for row in data:
                tree.insert("", "end", values=[str(item) if item is not None else "-" for item in row])
                
    except Exception as e:
        messagebox.showerror("Error", f"An error occurred: {str(e)}")

    # 添加关闭按钮
    Button(data_window, text="Close", command=data_window.destroy).grid(row=2, column=0, pady=10)

# --- Menu Frames ---
def show_search_trains_frame():
    clear_frame(main_window)
    Label(main_window, text="Search Trains", font=("Arial", 14)).pack(pady=10)

    # 出发站
    Label(main_window, text="Departure Station:").pack()
    dep_station_entry = Entry(main_window)
    dep_station_entry.pack(pady=5)

    # 到达站
    Label(main_window, text="Arrival Station:").pack()
    arr_station_entry = Entry(main_window)
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
        
        display_table(
            lambda: PriceService.search_available_tickets(dep_station, arr_station, departure_date),
            ["Train No", "Date", "From", "To", "Price", "Seats", "Type"]
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

    Button(main_window, text="Exit", command=main_window.quit, width=30).pack(pady=5)

def show_train_route_frame():
    clear_frame(main_window)
    Label(main_window, text="Train Route Information", font=("Arial", 14)).pack(pady=10)

    Label(main_window, text="Train Number:").pack()
    train_num_entry = Entry(main_window)
    train_num_entry.insert(0, "G1")
    train_num_entry.pack()
    
    Button(main_window, text="View Route", 
           command=lambda: display_table(
               lambda: TrainService.get_train_route(train_num_entry.get()),
               ["Order", "Station Name", "Code", "Arrival Time", "Departure Time", "Type"]
           )).pack(pady=5)

    Button(main_window, text="Back to Main Menu", command=show_main_menu_frame).pack(pady=20)

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

# --- Main Application Logic ---
def run_gui_app():
    global main_window
    main_window = tk.Tk()
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

    # Start with the main menu
    show_main_menu_frame()

    # When the main window is closed, ensure DB connection is closed
    main_window.protocol("WM_DELETE_WINDOW", on_closing)

    main_window.mainloop()
    db.close()  # Ensure database connection is closed after mainloop exits

def on_closing():
    if messagebox.askokcancel("Quit", "Do you want to quit the application?"):
        db.close()  # Close the database connection
        main_window.destroy()

if __name__ == "__main__":
    run_gui_app()