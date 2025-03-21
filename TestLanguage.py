import os
import time

# Словарь переводов
translations = {
    "choose_language": {
        "ru": "Выберите язык (ru/en): ",
        "en": "Choose language (ru/en): "
    },
    "invalid_input": {
        "ru": "Некорректный ввод. Попробуйте снова.",
        "en": "Invalid input. Try again."
    },
    "select_action": {
        "ru": "Выберите действие:",
        "en": "Select an action:"
    },
    "click_coords": {
        "ru": "Клик по координатам",
        "en": "Click by coordinates"
    },
    "click_image": {
        "ru": "Клик по изображению",
        "en": "Click by image"
    },
    "exit": {
        "ru": "Выход",
        "en": "Exit"
    },
    "enter_number": {
        "ru": "Введите номер: ",
        "en": "Enter number: "
    },
    "saved_actions": {
        "ru": "Сохраненные действия:",
        "en": "Saved actions:"
    },
    "execution": {
        "ru": "Выполняется итерация",
        "en": "Executing iteration"
    },
    "waiting": {
        "ru": "Ожидание",
        "en": "Waiting"
    },
    "window_not_found": {
        "en": "Window with HWND {hwnd} not found!",
        "ru": "Окно с HWND {hwnd} не найдено!"
    },
    "click_sent": {
        "en": "Click sent to window (HWND: {hwnd}) at coordinates: ({x}, {y})",
        "ru": "Отправлен клик в окно (HWND: {hwnd}) по координатам: ({x}, {y})"
    }
}

# Функция для перевода
def t(key,language,**kwargs):
    return translations[key][language].format(**kwargs)

# Запрос языка у пользователя
while True:
    print(t("choose_language","en"))
    print(t("choose_language","ru"))
    language = input().strip().lower()
    if language in ["ru", "en"]:
        break
    print(t("invalid_input"))

# Теперь можно использовать `t("some_key")` в коде

print(t("select_action",language))
print("1. " + t("click_coords",language))
print("2. " + t("click_image",language))
print("3. " + t("exit",language))

choice = input(t("enter_number",language))

hwnd = 12345  # Примерное значение
print(t("window_not_found", language, hwnd=hwnd))

hwnd = 12345
x, y = 300, 200
print(t("click_sent", language, hwnd=hwnd, x=x, y=y))