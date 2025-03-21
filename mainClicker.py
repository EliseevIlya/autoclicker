import time
import cv2
import numpy as np
import pyautogui

# Импорт из pywin32 для захвата окна
import win32gui
import win32ui
import win32con
import win32api


def get_window_screenshot(window_title, region=None):
    """
    Получает скриншот окна по его заголовку.
    Если region указан, то он должен быть кортежем (x, y, width, height) относительно клиентской области окна.
    """
    hwnd = win32gui.FindWindow(None, window_title)
    if hwnd == 0:
        print(f"Окно с заголовком '{window_title}' не найдено!")
        return None

    # Получаем координаты клиентской области окна (в относительных координатах)
    left, top, right, bottom = win32gui.GetClientRect(hwnd)
    # Преобразуем клиентские координаты в координаты экрана
    left, top = win32gui.ClientToScreen(hwnd, (left, top))
    right, bottom = win32gui.ClientToScreen(hwnd, (right, bottom))
    window_width = right - left
    window_height = bottom - top

    # Если задан регион, корректируем координаты и размеры
    if region:
        rx, ry, rw, rh = region
        # Обновляем левый верхний угол и размеры области
        left += rx
        top += ry
        window_width = rw
        window_height = rh

    # Получаем дескриптор контекста устройства окна
    hwindc = win32gui.GetWindowDC(hwnd)
    srcdc = win32ui.CreateDCFromHandle(hwindc)
    memdc = srcdc.CreateCompatibleDC()

    # Создаем совместимый объект Bitmap
    bmp = win32ui.CreateBitmap()
    bmp.CreateCompatibleBitmap(srcdc, window_width, window_height)
    memdc.SelectObject(bmp)

    # Захватываем изображение
    memdc.BitBlt((0, 0), (window_width, window_height), srcdc, (0, 0), win32con.SRCCOPY)

    # Получаем данные из Bitmap
    bmp_info = bmp.GetInfo()
    bmp_str = bmp.GetBitmapBits(True)
    img = np.frombuffer(bmp_str, dtype=np.uint8)
    img.shape = (window_height, window_width, 4)

    # Очистка ресурсов
    memdc.DeleteDC()
    win32gui.DeleteObject(bmp.GetHandle())
    win32gui.ReleaseDC(hwnd, hwindc)

    # Преобразуем BGRA в BGR (отбрасываем альфа-канал)
    img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
    return img


def click_at_coordinates(x, y):
    """Просто клик по заданным координатам (абсолютные координаты экрана)."""
    print(f"Клик по координатам: ({x}, {y})")
    pyautogui.click(x, y)


def click_by_image(template_path, window_title=None, region=None, threshold=0.8):
    """
    Ищет изображение (шаблон) в заданной области окна или на экране и кликает по центру найденного совпадения.

    :param template_path: путь к файлу изображения шаблона
    :param window_title: заголовок окна, из которого нужно сделать скриншот. Если None, используется весь экран.
    :param region: если указан window_title, region задаёт область относительно клиентской области окна,
                   иначе region используется как область экрана (left, top, width, height)
    :param threshold: порог точности совпадения
    :return: True, если клик совершен, иначе False
    """
    if window_title:
        screenshot = get_window_screenshot(window_title, region)
        if screenshot is None:
            return False
    else:
        screenshot = pyautogui.screenshot(region=region)
        screenshot = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)

    # Преобразуем в оттенки серого
    gray_screenshot = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)

    template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
    if template is None:
        print(f"Ошибка: не удалось загрузить шаблон {template_path}")
        return False

    result = cv2.matchTemplate(gray_screenshot, template, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

    if max_val >= threshold:
        # Определяем координаты центра найденного шаблона относительно скриншота
        center_x = max_loc[0] + template.shape[1] // 2
        center_y = max_loc[1] + template.shape[0] // 2

        if window_title:
            # Если скриншот делался из окна, вычисляем абсолютные координаты экрана.
            # Получаем положение окна на экране:
            hwnd = win32gui.FindWindow(None, window_title)
            if hwnd:
                win_left, win_top, _, _ = win32gui.GetWindowRect(hwnd)
                # Если region был указан, добавляем смещение:
                if region:
                    rx, ry, _, _ = region
                    abs_x = win_left + rx + center_x
                    abs_y = win_top + ry + center_y
                else:
                    abs_x = win_left + center_x
                    abs_y = win_top + center_y
            else:
                abs_x, abs_y = center_x, center_y
        else:
            abs_x, abs_y = center_x, center_y

        print(f"Найден шаблон {template_path} с точностью {max_val:.2f}. Кликаю по ({abs_x}, {abs_y})")
        pyautogui.click(abs_x, abs_y)
        return True
    else:
        print(f"Шаблон {template_path} не найден. Точность {max_val:.2f} меньше порога {threshold}")
        return False


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
        # Для типа image:
        'template_path': 'button.png',
        'window_title': 'NOX',           # заголовок окна, из которого брать скриншот
        'region': (500, 300, 400, 400),    # область относительно окна или экрана
        'threshold': 0.8       # необязательный, по умолчанию 0.8
    }
    """
    for action in actions:
        action_type = action.get('type')
        delay = action.get('delay', 1)  # задержка по умолчанию 1 секунда
        if action_type == 'coordinate':
            x = action.get('x')
            y = action.get('y')
            if x is None or y is None:
                print("Ошибка: для действия 'coordinate' нужны 'x' и 'y'")
            else:
                click_at_coordinates(x, y)
        elif action_type == 'image':
            template_path = action.get('template_path')
            window_title = action.get('window_title')  # если не указан, берется общий экран
            region = action.get('region')
            if template_path is None:
                print("Ошибка: для действия 'image' нужен 'template_path'")
            else:
                threshold = action.get('threshold', 0.8)
                click_by_image(template_path, window_title, region, threshold)
        else:
            print(f"Неизвестный тип действия: {action_type}")
        time.sleep(delay)


if __name__ == "__main__":
    # Пример последовательности действий:
    actions = [
        # Клик по координатам (например, меню) – абсолютные координаты экрана
        {
            'type': 'coordinate',
            'x': 627,
            'y': 806,
            'delay': 1.5  # задержка после клика
        },
        {
            'type': 'coordinate',
            'x': 866,
            'y': 965,
            'delay': 1.5
        },
        # Поиск и клик по кнопке через картинку внутри окна NOX
        {
            'type': 'image',
            'template_path': 'button.png',
            'window_title': 'GhostDragon',  # заголовок окна эмулятора
            'threshold': 0.8,
            'delay': 2
        },
        # Ещё один клик по координатам
        {
            'type': 'coordinate',
            'x': 1075,
            'y': 958,
            'delay': 1.5
        },
        {
            'type': 'coordinate',
            'x': 778,
            'y': 938,
            'delay': 1.5
        }
    ]

    # Запуск цикла, который будет выполнять последовательность действий.
    while True:
        run_click_sequence(actions)
        print("Завершена последовательность, ждём 120 секунд перед следующим циклом")
        time.sleep(120)
