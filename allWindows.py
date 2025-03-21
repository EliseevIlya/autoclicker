import win32gui

def enum_window_callback(hwnd, windows):
    # Проверяем, является ли окно видимым
    if win32gui.IsWindowVisible(hwnd):
        title = win32gui.GetWindowText(hwnd)
        if title:  # Если заголовок не пустой
            windows.append((hwnd, title))

def get_all_window_titles():
    windows = []
    win32gui.EnumWindows(enum_window_callback, windows)
    return windows

if __name__ == "__main__":
    window_list = get_all_window_titles()
    print("Найденные окна/ Finded Apps:")
    for hwnd, title in window_list:
        print(f"HWND: {hwnd} | Заголовок/Title: {title}")
