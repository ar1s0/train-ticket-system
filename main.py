import tkinter as tk
from tkinter import messagebox, simpledialog, Toplevel, Label, Entry, Button
from tkinter import ttk
import datetime

from services import TrainService, StationService, PriceService, TicketSalesService
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

def validate_date_input(date_str):
    """Validates and converts a YYYY-MM-DD string to a date object."""
    try:
        return datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return None

def display_table(get_data_func, tree):
    # 清除现有数据
    for item in tree.get_children():
        tree.delete(item)
    
    try:
        data, error = get_data_func()
        
        # 如果有错误消息，显示提示
        if error:
            messagebox.showinfo("Information", error)
        
        # 显示数据（即使有错误消息也显示可能存在的数据）
        if data:
            for row in data:
                try:
                    tree.insert('', 'end', values=row)
                except Exception as e:
                    messagebox.showerror("Error", f"Error inserting row: {str(e)}")
                    
    except Exception as e:
        messagebox.showerror("Error", f"An error occurred: {str(e)}")

# --- Menu Frames ---
def show_main_menu_frame():
    global main_window
    clear_frame(main_window)
    main_window.title("Train Ticket System - Information Display")

    Label(main_window, text="Information Display Menu", font=("Arial", 16)).pack(pady=20)

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

    Button(main_window, text="View Available Tickets", 
           command=show_ticket_info_frame, width=30).pack(pady=5)

    Button(main_window, text="Exit", command=main_window.quit, width=30).pack(pady=5)

def show_price_info_frame():
    clear_frame(main_window)
    Label(main_window, text="Price Information", font=("Arial", 14)).pack(pady=10)

    Label(main_window, text="Train Number:").pack()
    train_num_entry = Entry(main_window)
    train_num_entry.pack()
    
    Button(main_window, text="List Prices", 
           command=lambda: display_table(
               lambda: PriceService.list_prices_for_train(train_num_entry.get()),
               ["Departure", "Arrival", "Seat Type", "Price"]
           )).pack(pady=5)

    Button(main_window, text="Back to Main Menu", command=show_main_menu_frame).pack(pady=20)

def show_ticket_info_frame():
    clear_frame(main_window)
    Label(main_window, text="Available Ticket Information", font=("Arial", 14)).pack(pady=10)

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
                    lambda: results,
                    ["Train", "Date", "Departure", "Arrival", "Seat Type", "Price", "Seats"]
                )
            else:
                show_message("Search Results", "No tickets found for your criteria.")
        else:
            show_error("Invalid Date", "Please enter date in YYYY-MM-DD format.")

    Button(main_window, text="Search Tickets", command=search_action).pack(pady=5)
    Button(main_window, text="Back to Main Menu", command=show_main_menu_frame).pack(pady=20)

# --- Main Application Logic ---
def run_gui_app():
    global main_window
    main_window = tk.Tk()
    main_window.title("Train Station Ticket Information System")
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