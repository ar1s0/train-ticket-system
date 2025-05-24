import tkinter as tk
from tkinter import messagebox, simpledialog, Toplevel, Label, Entry, Button
from tkinter import ttk  # 新增导入ttk模块
import datetime

# Import your existing backend logic
from auth import AuthManager
from services import TrainService, StationService, PriceService, TicketSalesService
from models import Salesperson
from database import db  # For closing DB connection
from db_setup import setup_database  # NEW: Import the database setup function

# --- Global Variables ---
current_user = None
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

def validate_date_input(date_str):
    """Validates and converts a YYYY-MM-DD string to a date object."""
    try:
        return datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return None

def display_table(title, headers, data):
    """Display data in a table format in a new window."""
    if not data:
        show_message("No Data", "No data to display.")
        return
    
    table_window = Toplevel(main_window)
    table_window.title(title)
    
    # Create Treeview widget
    tree = ttk.Treeview(table_window, columns=headers, show='headings')
    
    # Set column headings
    for col in headers:
        tree.heading(col, text=col)
        tree.column(col, width=100, anchor='center')
    
    # Add data rows
    for row in data:
        tree.insert('', 'end', values=row)
    
    # Add scrollbar
    scrollbar = ttk.Scrollbar(table_window, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)
    
    # Pack widgets
    tree.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    
    # Adjust window size
    table_window.geometry(f"{min(len(headers)*150, 800)}x400")

# --- Login & Authentication UI ---
def login_gui():
    global current_user, main_window

    login_window = Toplevel(main_window)
    login_window.title("Login / Register")
    login_window.geometry("300x250")
    login_window.grab_set()  # Make it modal

    Label(login_window, text="Salesperson ID:").pack(pady=5)
    id_entry = Entry(login_window)
    id_entry.pack(pady=2)

    Label(login_window, text="Password:").pack(pady=5)
    pass_entry = Entry(login_window, show="*")
    pass_entry.pack(pady=2)

    def perform_login():
        global current_user  # Allow modifying global current_user
        salesperson_id = id_entry.get()
        password = pass_entry.get()
        user = AuthManager.login(salesperson_id, password)
        if user:
            current_user = user
            show_message("Login Success", f"Welcome, {current_user.salesperson_name} ({current_user.role})!")
            login_window.destroy()
            show_main_menu_frame()  # Show the main menu after successful login
        else:
            show_error("Login Failed", "Invalid credentials. Please try again.")

    def register_salesperson_gui():
        reg_window = Toplevel(login_window)
        reg_window.title("Register Salesperson")
        reg_window.grab_set()

        Label(reg_window, text="Admin ID:").pack()
        admin_id_entry = Entry(reg_window)
        admin_id_entry.pack()

        Label(reg_window, text="Admin Password:").pack()
        admin_pass_entry = Entry(reg_window, show="*")
        admin_pass_entry.pack()

        Label(reg_window, text="New Salesperson ID:").pack()
        new_id_entry = Entry(reg_window)
        new_id_entry.pack()

        Label(reg_window, text="New Salesperson Name:").pack()
        new_name_entry = Entry(reg_window)
        new_name_entry.pack()

        Label(reg_window, text="New Salesperson Contact:").pack()
        new_contact_entry = Entry(reg_window)
        new_contact_entry.pack()

        Label(reg_window, text="New Salesperson Email:").pack()
        new_email_entry = Entry(reg_window)
        new_email_entry.pack()

        Label(reg_window, text="New Salesperson Password:").pack()
        new_pass_entry = Entry(reg_window, show="*")
        new_pass_entry.pack()

        Label(reg_window, text="Role (Salesperson/Admin):").pack()
        new_role_entry = Entry(reg_window)
        new_role_entry.insert(0, "Salesperson")  # Default role
        new_role_entry.pack()

        def perform_register():
            admin_id = admin_id_entry.get()
            admin_password = admin_pass_entry.get()
            admin_check_user = AuthManager.login(admin_id, admin_password)

            if admin_check_user and admin_check_user.role == 'Admin':
                success = AuthManager.register_salesperson(
                    new_id_entry.get(),
                    new_name_entry.get(),
                    new_contact_entry.get(),
                    new_email_entry.get(),
                    new_pass_entry.get(),
                    new_role_entry.get()
                )
                if success:
                    show_message("Registration Success", "New salesperson registered!")
                    reg_window.destroy()
                else:
                    show_error("Registration Failed", "Could not register salesperson. ID might exist.")
            else:
                show_error("Permission Denied", "Only an Admin can register new salespersons.")

        Button(reg_window, text="Register", command=perform_register).pack(pady=10)

    Button(login_window, text="Login", command=perform_login).pack(pady=5)
    Button(login_window, text="Register New Salesperson (Admin)", command=register_salesperson_gui).pack(pady=5)
    Button(login_window, text="Exit Application", command=main_window.quit).pack(pady=5)

# --- Menu Frames ---
def show_main_menu_frame():
    global main_window, current_user
    clear_frame(main_window)
    main_window.title(f"Train Ticket System - Logged in as: {current_user.salesperson_name} ({current_user.role})")

    Label(main_window, text="Main Menu", font=("Arial", 16)).pack(pady=20)

    Button(main_window, text="Train Management", command=show_train_management_frame, width=30).pack(pady=5)
    Button(main_window, text="Station Management", command=show_station_management_frame, width=30).pack(pady=5)
    Button(main_window, text="Price Management", command=show_price_management_frame, width=30).pack(pady=5)
    Button(main_window, text="Ticket Sales & Refund", command=show_ticket_sales_frame, width=30).pack(pady=5)
    Button(main_window, text="Statistics", command=show_statistics_frame, width=30).pack(pady=5)
    Button(main_window, text="Logout", command=logout, width=30).pack(pady=5)
    Button(main_window, text="Exit", command=main_window.quit, width=30).pack(pady=5)

def show_train_management_frame():
    if not current_user or current_user.role != 'Admin':
        show_error("Permission Denied", "Admin role required for Train Management.")
        return

    clear_frame(main_window)
    Label(main_window, text="Train Management", font=("Arial", 14)).pack(pady=10)

    # Add Train UI
    Label(main_window, text="--- Add New Train ---").pack(pady=5)
    Label(main_window, text="Train Number:").pack()
    train_num_entry = Entry(main_window)
    train_num_entry.pack()
    Label(main_window, text="Train Type:").pack()
    train_type_entry = Entry(main_window)
    train_type_entry.pack()
    Label(main_window, text="Total Seats:").pack()
    total_seats_entry = Entry(main_window)
    total_seats_entry.pack()
    Label(main_window, text="Departure Station Name:").pack()
    dep_station_entry = Entry(main_window)
    dep_station_entry.pack()
    Label(main_window, text="Arrival Station Name:").pack()
    arr_station_entry = Entry(main_window)
    arr_station_entry.pack()

    def add_train_action():
        try:
            total_seats = int(total_seats_entry.get())
            success = TrainService.add_train(
                train_num_entry.get(), train_type_entry.get(),
                total_seats, dep_station_entry.get(), arr_station_entry.get()
            )
            if success:
                show_message("Success", "Train added.")
            else:
                show_error("Error", "Failed to add train.")
        except ValueError:
            show_error("Invalid Input", "Total Seats must be a number.")

    Button(main_window, text="Add Train", command=add_train_action).pack(pady=5)

    Button(main_window, text="List All Trains", 
           command=lambda: display_table(
               "All Trains",
               ["Train No", "Type", "Seats", "Departure", "Arrival"],
               TrainService.list_all_trains()
           )).pack(pady=10)

    Button(main_window, text="Back to Main Menu", command=show_main_menu_frame).pack(pady=20)

def show_station_management_frame():
    if not current_user or current_user.role != 'Admin':
        show_error("Permission Denied", "Admin role required for Station Management.")
        return

    clear_frame(main_window)
    Label(main_window, text="Station Management", font=("Arial", 14)).pack(pady=10)

    # Add Station UI
    Label(main_window, text="--- Add New Station ---").pack(pady=5)
    Label(main_window, text="Station Name:").pack()
    station_name_entry = Entry(main_window)
    station_name_entry.pack()
    Label(main_window, text="Station Code (Optional):").pack()
    station_code_entry = Entry(main_window)
    station_code_entry.pack()

    def add_station_action():
        success = StationService.add_station(
            station_name_entry.get(),
            station_code_entry.get() if station_code_entry.get() else None
        )
        if success:
            show_message("Success", "Station added.")
        else:
            show_error("Error", "Failed to add station. Name might exist.")

    Button(main_window, text="Add Station", command=add_station_action).pack(pady=5)

    Button(main_window, text="List All Stations", 
           command=lambda: display_table(
               "All Stations",
               ["ID", "Name", "Code"],
               StationService.list_all_stations()
           )).pack(pady=10)

    Button(main_window, text="Back to Main Menu", command=show_main_menu_frame).pack(pady=20)

def show_price_management_frame():
    if not current_user or current_user.role != 'Admin':
        show_error("Permission Denied", "Admin role required for Price Management.")
        return

    clear_frame(main_window)
    Label(main_window, text="Price Management", font=("Arial", 14)).pack(pady=10)

    Label(main_window, text="--- Add Price Rule ---").pack(pady=5)
    Label(main_window, text="Train Number:").pack()
    train_num_entry = Entry(main_window)
    train_num_entry.pack()
    Label(main_window, text="Departure Station Name:").pack()
    dep_station_entry = Entry(main_window)
    dep_station_entry.pack()
    Label(main_window, text="Arrival Station Name:").pack()
    arr_station_entry = Entry(main_window)
    arr_station_entry.pack()
    Label(main_window, text="Seat Type (e.g., 'Second Class'):").pack()
    seat_type_entry = Entry(main_window)
    seat_type_entry.pack()
    Label(main_window, text="Price:").pack()
    price_entry = Entry(main_window)
    price_entry.pack()

    def add_price_action():
        try:
            price_amount = float(price_entry.get())
            success = PriceService.add_price(
                train_num_entry.get(), dep_station_entry.get(), arr_station_entry.get(),
                seat_type_entry.get(), price_amount
            )
            if success:
                show_message("Success", "Price rule added.")
            else:
                show_error("Error", "Failed to add price rule.")
        except ValueError:
            show_error("Invalid Input", "Price must be a number.")

    Button(main_window, text="Add Price Rule", command=add_price_action).pack(pady=5)

    Label(main_window, text="--- List Prices for a Train ---").pack(pady=5)
    Label(main_window, text="Train Number:").pack()
    list_train_num_entry = Entry(main_window)
    list_train_num_entry.pack()
    Button(main_window, text="List Prices", 
           command=lambda: display_table(
               f"Prices for Train {list_train_num_entry.get()}",
               ["Departure", "Arrival", "Seat Type", "Price"],
               PriceService.list_prices_for_train(list_train_num_entry.get())
           )).pack(pady=5)

    Button(main_window, text="Back to Main Menu", command=show_main_menu_frame).pack(pady=20)

def show_ticket_sales_frame():
    if not current_user:
        show_error("Login Required", "Please log in to perform ticket operations.")
        return

    clear_frame(main_window)
    Label(main_window, text="Ticket Sales & Refund", font=("Arial", 14)).pack(pady=10)

    # Search Available Tickets UI (simplified)
    Label(main_window, text="--- Search Tickets ---").pack(pady=5)
    Label(main_window, text="Departure Station:").pack()
    search_dep_entry = Entry(main_window)
    search_dep_entry.pack()
    Label(main_window, text="Arrival Station:").pack()
    search_arr_entry = Entry(main_window)
    search_arr_entry.pack()
    Label(main_window, text="Departure Date (YYYY-MM-DD):").pack()
    search_date_entry = Entry(main_window)
    search_date_entry.pack()

    def search_action():
        dep_station = search_dep_entry.get()
        arr_station = search_arr_entry.get()
        date_str = search_date_entry.get()
        dep_date = validate_date_input(date_str)

        if dep_date:
            results = TicketSalesService.search_available_tickets(dep_station, arr_station, dep_date)
            if results:
                display_table(
                    "Available Tickets",
                    ["Train", "Date", "Departure", "Arrival", "Seat Type", "Price", "Seats"],
                    [
                        [
                            r['train_number'],
                            str(r['departure_date']),
                            r['departure_station_name'],
                            r['arrival_station_name'],
                            r['seat_type'],
                            f"${r['price']:.2f}",
                            r['remaining_seats']
                        ]
                        for r in results
                    ]
                )
            else:
                show_message("Search Results", "No tickets found for your criteria.")
        else:
            show_error("Invalid Date", "Please enter date in YYYY-MM-DD format.")

    Button(main_window, text="Search Tickets", command=search_action).pack(pady=5)

    # Sell Ticket UI (simplified, more detailed in a real app)
    Label(main_window, text="--- Sell Ticket ---").pack(pady=5)
    Label(main_window, text="Train Number:").pack()
    sell_train_num_entry = Entry(main_window)
    sell_train_num_entry.pack()
    Label(main_window, text="Departure Date (YYYY-MM-DD):").pack()
    sell_dep_date_entry = Entry(main_window)
    sell_dep_date_entry.pack()
    Label(main_window, text="Seat Number:").pack()
    sell_seat_num_entry = Entry(main_window)
    sell_seat_num_entry.pack()
    Label(main_window, text="Passenger Name:").pack()
    sell_passenger_name_entry = Entry(main_window)
    sell_passenger_name_entry.pack()
    Label(main_window, text="ID Type:").pack()
    sell_id_type_entry = Entry(main_window)
    sell_id_type_entry.pack()
    Label(main_window, text="ID Number:").pack()
    sell_id_number_entry = Entry(main_window)
    sell_id_number_entry.pack()
    Label(main_window, text="Ticket Price:").pack()
    sell_price_entry = Entry(main_window)
    sell_price_entry.pack()
    Label(main_window, text="Departure Station Name:").pack()
    sell_dep_station_entry = Entry(main_window)
    sell_dep_station_entry.pack()
    Label(main_window, text="Arrival Station Name:").pack()
    sell_arr_station_entry = Entry(main_window)
    sell_arr_station_entry.pack()

    def sell_action():
        dep_date = validate_date_input(sell_dep_date_entry.get())
        if not dep_date:
            show_error("Invalid Date", "Please enter date in YYYY-MM-DD format.")
            return

        try:
            ticket_price = float(sell_price_entry.get())
            success = TicketSalesService.sell_ticket(
                sell_train_num_entry.get(), dep_date, sell_seat_num_entry.get(),
                sell_passenger_name_entry.get(), sell_id_type_entry.get(), sell_id_number_entry.get(),
                sell_dep_station_entry.get(), sell_arr_station_entry.get(),
                ticket_price, current_user.salesperson_id
            )
            if success:
                show_message("Success", "Ticket sold!")
            else:
                show_error("Error", "Failed to sell ticket. Check availability or data.")
        except ValueError:
            show_error("Invalid Input", "Ticket price must be a number.")

    Button(main_window, text="Sell Ticket", command=sell_action).pack(pady=5)

    # Refund Ticket UI (simplified)
    Label(main_window, text="--- Refund Ticket ---").pack(pady=5)
    Label(main_window, text="Order ID:").pack()
    refund_order_id_entry = Entry(main_window)
    refund_order_id_entry.pack()
    Label(main_window, text="Refund Amount:").pack()
    refund_amount_entry = Entry(main_window)
    refund_amount_entry.pack()

    def refund_action():
        try:
            refund_amount = float(refund_amount_entry.get())
            success = TicketSalesService.refund_ticket(
                refund_order_id_entry.get(), refund_amount, current_user.salesperson_id
            )
            if success:
                show_message("Success", "Ticket refunded!")
            else:
                show_error("Error", "Failed to refund ticket. Check Order ID or status.")
        except ValueError:
            show_error("Invalid Input", "Refund amount must be a number.")

    Button(main_window, text="Refund Ticket", command=refund_action).pack(pady=5)

    Button(main_window, text="Back to Main Menu", command=show_main_menu_frame).pack(pady=20)

def show_statistics_frame():
    if not current_user:
        show_error("Login Required", "Please log in to view statistics.")
        return

    clear_frame(main_window)
    Label(main_window, text="Statistics", font=("Arial", 14)).pack(pady=10)

    # Train Sales Summary
    Label(main_window, text="--- Train Sales Summary ---").pack(pady=5)
    Label(main_window, text="Train Number:").pack()
    stats_train_num_entry = Entry(main_window)
    stats_train_num_entry.pack()
    Label(main_window, text="Departure Date (YYYY-MM-DD):").pack()
    stats_dep_date_entry = Entry(main_window)
    stats_dep_date_entry.pack()

    def get_train_summary_action():
        dep_date = validate_date_input(stats_dep_date_entry.get())
        if dep_date:
            result = TicketSalesService.get_train_sales_summary(stats_train_num_entry.get(), dep_date)
            if result:
                display_table(
                    f"Sales Summary for Train {stats_train_num_entry.get()}",
                    ["Metric", "Value"],
                    [
                        ["Total Tickets Sold", result.get('total_tickets_sold', 0)],
                        ["Total Sales Amount", f"${result.get('total_sales_amount', 0.00):.2f}"]
                    ]
                )
            else:
                show_message("No Data", "No sales data found for this train and date.")
        else:
            show_error("Invalid Date", "Please enter date in YYYY-MM-DD format.")

    Button(main_window, text="Get Train Sales Summary", command=get_train_summary_action).pack(pady=5)

    # Salesperson Daily Revenue
    Label(main_window, text="--- Salesperson Daily Revenue ---").pack(pady=5)
    Label(main_window, text="Sales Date (YYYY-MM-DD):").pack()
    sales_date_entry = Entry(main_window)
    sales_date_entry.pack()

    def get_salesperson_revenue_action():
        sales_date = validate_date_input(sales_date_entry.get())
        if sales_date:
            results = TicketSalesService.get_salesperson_daily_revenue(sales_date)
            if results:
                display_table(
                    f"Salesperson Revenue for {sales_date}",
                    ["Salesperson ID", "Name", "Total Revenue"],
                    [
                        [r['salesperson_id'], r['salesperson_name'], f"${r['total_revenue']:.2f}"]
                        for r in results
                    ]
                )
            else:
                show_message("No Data", "No revenue data found for this date.")
        else:
            show_error("Invalid Date", "Please enter date in YYYY-MM-DD format.")

    Button(main_window, text="Get Salesperson Daily Revenue", command=get_salesperson_revenue_action).pack(pady=5)

    Button(main_window, text="Back to Main Menu", command=show_main_menu_frame).pack(pady=20)

def logout():
    global current_user
    confirm = messagebox.askyesno("Logout", "Are you sure you want to log out?")
    if confirm:
        current_user = None
        show_message("Logged Out", "You have been logged out.")
        login_gui()  # Go back to the login screen
    else:
        show_main_menu_frame()

# --- Main Application Logic ---
def run_gui_app():
    global main_window
    main_window = tk.Tk()
    main_window.title("Train Station Ticket Management System")
    main_window.geometry("500x700")

    # NEW: Attempt to set up the database before anything else
    print("Initializing database setup...")
    if setup_database():
        print("Database initialized successfully!")
    else:
        show_error("Database Setup Failed", "Could not set up the database. Check your MySQL connection and permissions.")
        # If setup fails, it's better to exit or prevent further execution
        main_window.destroy()
        return

    # Initial screen will be the login screen
    login_gui()

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