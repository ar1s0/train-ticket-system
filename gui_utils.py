from tkinter import Toplevel, Label, Button
from tkinter import messagebox
import datetime
import tkinter as tk


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

