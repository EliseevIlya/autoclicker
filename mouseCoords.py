import pyautogui
from pynput import mouse


def on_click(x, y, button, pressed):
    # Выводим координаты только при нажатии кнопки
    if pressed:
        print(f"Клик зафиксирован: координаты ({x}, {y})")



if __name__ == "__main__":
    pyautogui.click(627, 806)
    # Запускаем слушатель событий мыши
    with mouse.Listener(on_click=on_click) as listener:
        listener.join()

