import os
import time
import cv2
import numpy as np
import pyautogui
from pynput import mouse
from concurrent.futures import Future
from language import translations
import json
import tkinter as tk
from tkinter import filedialog

# Импорт из pywin32 для работы с окном
import win32gui
import win32ui
import win32con
import win32api


def get_window_screenshot(hwnd, region=None):
    """
    Получает скриншот окна по его HWND.
    Если region указан, то он должен быть кортежем (x, y, width, height) относительно клиентской области окна.
    """
    if not win32gui.IsWindow(hwnd):
        #print(f"Окно с HWND {hwnd} не найдено!")
        print(t("window_not_found", language, hwnd=hwnd))
        return None

    # Получаем координаты клиентской области окна (относительно окна)
    left, top, right, bottom = win32gui.GetClientRect(hwnd)
    # Преобразуем клиентские координаты в координаты экрана
    left, top = win32gui.ClientToScreen(hwnd, (left, top))
    right, bottom = win32gui.ClientToScreen(hwnd, (right, bottom))
    window_width = right - left
    window_height = bottom - top

    # Если указан регион, корректируем координаты и р азмеры
    if region:
        rx, ry, rw, rh = region
        left += rx
        top += ry
        window_width = rw
        window_height = rh

    hwindc = win32gui.GetWindowDC(hwnd)
    srcdc = win32ui.CreateDCFromHandle(hwindc)
    memdc = srcdc.CreateCompatibleDC()

    bmp = win32ui.CreateBitmap()
    bmp.CreateCompatibleBitmap(srcdc, window_width, window_height)
    memdc.SelectObject(bmp)

    memdc.BitBlt((0, 0), (window_width, window_height), srcdc, (0, 0), win32con.SRCCOPY)

    bmp_str = bmp.GetBitmapBits(True)
    img = np.frombuffer(bmp_str, dtype=np.uint8)
    img.shape = (window_height, window_width, 4)

    memdc.DeleteDC()
    win32gui.DeleteObject(bmp.GetHandle())
    win32gui.ReleaseDC(hwnd, hwindc)

    img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
    return img


def click_in_window(hwnd, x, y):
    """
    Отправляет сообщения клика в окно с заданными координатами (относительно клиентской области окна).
    Эта функция не перемещает курсор, а отправляет WM_LBUTTONDOWN и WM_LBUTTONUP в указанное окно.
    """
    if not win32gui.IsWindow(hwnd):
        #print(f"Окно с HWND {hwnd} не найдено!")
        print(t("window_not_found", language, hwnd=hwnd))
        return

    # Формируем lParam: x в младшем слове, y в старшем.
    lParam = (y << 16) | (x & 0xFFFF)
    # Отправляем сообщения
    win32api.PostMessage(hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lParam)
    win32api.PostMessage(hwnd, win32con.WM_LBUTTONUP, 0, lParam)
    #print(f"Отправлен клик в окно (HWND: {hwnd}) по координатам: ({x}, {y})")
    print(t("click_sent", language, hwnd=hwnd, x=x, y=y))


def click_by_image(template_path, hwnd=None, region=None, threshold=0.8):
    """
    Ищет изображение (шаблон) в заданной области окна или на экране и кликает по центру найденного совпадения.
    Если задан hwnd, скриншот берётся из окна, а клик отправляется в это окно.
    Если hwnd не указан, используется клик через pyautogui (реальный курсор).
    """
    if hwnd:
        screenshot = get_window_screenshot(hwnd, region)
        if screenshot is None:
            return False
    else:
        screenshot = pyautogui.screenshot(region=region)
        screenshot = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)

    gray_screenshot = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)

    template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
    if template is None:
        #print(f"Ошибка: не удалось загрузить шаблон {template_path}")
        print(t("template_load_error", language, template_path=template_path))
        return False

    result = cv2.matchTemplate(gray_screenshot, template, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

    if max_val >= threshold:
        center_x = max_loc[0] + template.shape[1] // 2
        center_y = max_loc[1] + template.shape[0] // 2

        if hwnd:
            # Получаем положение окна на экране (для расчёта абсолютных координат, если нужно)
            win_left, win_top, _, _ = win32gui.GetWindowRect(hwnd)
            if region:
                rx, ry, _, _ = region
                local_x = rx + center_x
                local_y = ry + center_y
            else:
                local_x = center_x
                local_y = center_y

            # Отправляем сообщения клика в окно по вычисленным координатам
            click_in_window(hwnd, local_x, local_y)
        else:
            # Если hwnd не указан, используем обычный клик через pyautogui
            abs_x, abs_y = center_x, center_y
            #print(f"Найден шаблон {template_path} с точностью {max_val:.2f}. Кликаю по ({abs_x}, {abs_y})")
            print(t("template_found_and_click", language, template_path=template_path, max_val=max_val, abs_x=abs_x,
                    abs_y=abs_y))
            pyautogui.click(abs_x, abs_y)
        return True
    else:
        #print(f"Шаблон {template_path} не найден. Точность {max_val:.2f} меньше порога {threshold}")
        print(t("template_not_found", language, template_path=template_path, max_val=max_val, threshold=threshold))
        time.sleep(2)
        click_by_image(template_path, hwnd, region, threshold)
        #TODO добавить что после определенного количества он скипает и ищет следующую
        #и если не нашел то стоп


def run_click_sequence(actions):
    """
    Выполняет заданную последовательность действий.
    Каждый элемент в actions – словарь с настройками действия.

    Пример структуры action:
    {
        'type': 'coordinate',  # или 'image'
        'delay': 1.5,          # задержка после выполнения клика (сек)
        # Для типа coordinate:
        'x': 100,
        'y': 200,
        'hwnd': 198090,       # если указан, клик будет отправлен в это окно (без смены фокуса)
        # Для типа image:
        'template_path': 'button.png',
        'hwnd': 198090,       # окно, в котором производится поиск и клик
        'region': (50, 50, 400, 300),  # область внутри окна (необязательно)
        'threshold': 0.8
    }
    """
    for action in actions:
        action_type = action.get('type')
        delay = action.get('delay', 1)
        if action_type == 'coordinate':
            x = action.get('x')
            y = action.get('y')
            hwnd = action.get('hwnd')
            if x is None or y is None:
                #print("Ошибка: для действия 'coordinate' нужны 'x' и 'y'")
                print(t("coordinate_x_y_error", language))
            else:
                if hwnd:
                    # Отправляем клик через сообщения в окно
                    click_in_window(hwnd, x, y)
                else:
                    # Если hwnd не указан, используем pyautogui
                    #print(f"Клик по координатам: ({x}, {y})")
                    print(t("click_on", language, x=x, y=y))
                    pyautogui.click(x, y)
        elif action_type == 'image':
            template_path = action.get('template_path')
            hwnd = action.get('hwnd')
            region = action.get('region')
            if template_path is None:
                #print("Ошибка: для действия 'image' нужен 'template_path'")
                print(t("image_template_path_error", language))
            else:
                threshold = action.get('threshold', 0.8)
                click_by_image(template_path, hwnd, region, threshold)
        else:
            #print(f"Неизвестный тип действия: {action_type}")
            print(t("unknown_type_action", language, action_type=action_type))
        time.sleep(delay)


def get_all_window_titles():
    windows = []

    def enum_window_callback(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if title:
                windows.append((hwnd, title))

    win32gui.EnumWindows(enum_window_callback, None)
    return windows


def choose_hwnd():
    windows = get_all_window_titles()
    if not windows:
        #print("Не найдено открытых окон.")
        print(t("no_open_windows", language))
        return None

    #print("Выберите окно (введите номер):")
    print(t("choose_window", language))
    for i, (hwnd, title) in enumerate(windows, 1):
        #print(f"{i}. HWND: {hwnd} | Заголовок: {title}")
        print(t("HWND_title", language, i=i, hwnd=hwnd, title=title))

    while True:
        #choice = input("Введите номер окна: ")
        choice = input(t("window_number_input", language))
        if choice.isdigit():
            choice = int(choice)
            if 1 <= choice <= len(windows):
                return windows[choice - 1][0]
        #print("Некорректный ввод. Попробуйте снова.")
        print(t("invalid_input", language))


click_count = 0


def on_click(x, y, button, pressed, future):
    global click_count
    if pressed:
        click_count += 1
        if click_count == 1:
            #print("Окно открыто! Сделайте второй клик для фиксации координат.")
            print(t("window_opened_second_click", language))
        elif click_count == 2:
            future.set_result((x, y))  # Запоминаем координаты
            #print(f"Клик зафиксирован: координаты ({x}, {y})")
            print(t("click_recorded", language, x=x, y=y))
            return False  # Останавливаем прослушивание


def t(key, language, **kwargs):
    return translations[key][language].format(**kwargs)


def set_actions():
    global click_count
    actions = []
    hwnd = None

    #print("Выберите режим клика:")
    #print("1. По всему экрану")
    #print("2. Внутри окна (HWND)")

    print(t("click_mode", language))
    print("1. ", t("all_screen", language))
    print("2. ", t("inside_window_HWND", language))

    #mode = input("Введите номер: ")
    mode = input(t("input_mode_number", language))
    if mode == "2":
        hwnd = choose_hwnd()

    while True:
        #print("Выберите действие:")
        #print("1. Клик по координатам")
        #print("2. Клик по изображению")
        #print("3. Завершить и запустить кликер")

        print(t("select_action", language))
        print("1. ", t("click_coords", language))
        print("2. ", t("click_image", language))
        print("3. ", t("exit", language))

        #choice = input("Введите номер: ")
        choice = input(t("enter_number", language))

        if choice == "1":
            future = Future()
            click_count = 0
            #print("Откройте окно")
            print(t("open_window", language))
            with mouse.Listener(on_click=lambda x, y, b, p: on_click(x, y, b, p, future)) as listener:
                listener.join()
            x, y = future.result()
            #delay = float(input("Введите задержку (сек): "))
            delay = float(input(t("enter_delay", language)))
            action = {'type': 'coordinate', 'x': x, 'y': y, 'delay': delay}
            if hwnd:
                action['hwnd'] = hwnd
            actions.append(action)

        elif choice == "2":
            #template_path = input("Введите путь к изображению: ")
            #threshold = float(input("Введите порог совпадения (0-1): "))
            #delay = float(input("Введите задержку (сек): "))

            template_path = input(t("image_path", language))
            threshold = float(input(t("match_threshold", language)))
            delay = float(input(t("enter_delay", language)))

            action = {'type': 'image', 'template_path': template_path, 'threshold': threshold, 'delay': delay}
            if hwnd:
                action['hwnd'] = hwnd
            actions.append(action)

        elif choice == "3":
            break

        else:
            #print("Некорректный ввод. Попробуйте снова.")
            print(t("invalid_input", language))

    # Запрашиваем у пользователя количество операций
    #operations_input = input("Введите количество операций (или 'true' для бесконечного выполнения): ").strip().lower()
    operations_input = input(t("operations_number", language)).strip().lower()

    # Определяем количество операций
    if operations_input == 'true':
        infinite = True
        operations_count = 0
    else:
        try:
            operations_count = int(operations_input)
            infinite = False
        except ValueError:
            #print("Ошибка: Введите число или 'true'!")
            print(t("operations_number_error", language))
            exit()
    try:
        #sleep_time = int(input("Введите время задержки между операциями (в секундах): ").strip())
        sleep_time = int(input(t("operations_delay", language)).strip())

    except ValueError:
        #print("Ошибка: Введите число!")
        print(t("operations_delay_error", language))
        exit()

    #print("Сохраненные действия:")
    print(t("saved_actions", language))
    for act in actions:
        print(act)

    return actions, operations_count, infinite, sleep_time


language = "en"


def language_choose():
    global language

    #TODO переписать в цикл чтобы выводил все варианты для choose_language и invalid_input
    while True:
        print(t("choose_language", "en"))
        print(t("choose_language", "ru"))
        language = input().strip().lower()
        if language in ["ru", "en"]:
            break
        print(t("invalid_input", "en"))
        print(t("invalid_input", "ru"))


def import_data():
    """Импортирует данные из файла"""
    root = tk.Tk()
    root.withdraw()  # Скрываем основное окно
    root.attributes('-topmost', True)  # Делаем диалог поверх всех окон
    file_path = filedialog.askopenfilename(title=t("import_title",language), filetypes=[("Text Files", "*.txt")])
    root.destroy()

    if file_path:
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                data = json.load(file)  # Читаем JSON
                return data.get("actions", []), data.get("operations_count", 0), data.get("infinite", False), data.get(
                    "sleep_time", 1)
        except Exception as e:
            #print(f"Ошибка при импорте: {e}")
            print(t( "import_error",language,e=e))

    return [], 0, False, 1


def export_data(actions, operations_count, infinite, sleep_time):
    """Экспортирует данные в файл"""
    root = tk.Tk()
    root.withdraw()  # Скрываем основное окно
    root.attributes('-topmost', True)  # Делаем диалог поверх всех окон
    file_path = filedialog.asksaveasfilename(title=t("export_title",language),
                                             defaultextension=".txt",
                                             filetypes=[("Text Files", "*.txt")])
    root.destroy()

    if file_path:
        try:
            with open(file_path, "w", encoding="utf-8") as file:
                json.dump({
                    "actions": actions,
                    "operations_count": operations_count,
                    "infinite": infinite,
                    "sleep_time": sleep_time
                }, file, ensure_ascii=False, indent=4)
            #print("Данные успешно сохранены!")
            print(t("export_save",language))
        except Exception as e:
            #print(f"Ошибка при экспорте: {e}")
            print(t("export_error",language,e=e))


if __name__ == "__main__":

    language_choose()

    #print("Хотите импортировать данные из файла? (yes/no)")
    print(t("import",language))
    if input().strip().lower() == "yes":
        actions, operations_count, infinite, sleep_time = import_data()
    else:
        actions, operations_count, infinite, sleep_time = set_actions()

    #print("Хотите экспортировать данные? (yes/no)")
    print(t("export",language))
    if input().strip().lower() == "yes":
        export_data(actions, operations_count, infinite, sleep_time)

    #actions, operations_count, infinite, sleep_time = set_actions()
    #print(actions, operations_count, infinite, sleep_time)

    print(t("start_clicker",language))
    start_action = input().strip().lower()
    if start_action  == "yes":
        i = 0
        while infinite or i < operations_count:
            #print(f"Выполняется итерация {i + 1}...")
            print(t("iteration_run", language, i=i + 1))

            run_click_sequence(actions)

            i += 1
            #print(f"Ожидание {sleep_time} секунд перед следующей итерацией...")
            print(t("sleep", language, sleep_time=sleep_time))
            time.sleep(sleep_time)
    elif start_action == "no":
        exit()