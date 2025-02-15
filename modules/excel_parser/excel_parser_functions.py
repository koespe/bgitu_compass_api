import re


def make_dict_day(data):
    template = dict(
        subjectName=data.get("subjectName"),
        building=data.get("building"),
        startAt=str(data.get("startAt")),
        endAt=str(data.get("endAt")),
        classroom=data.get("classroom"),
        teacher=data.get("teacher"),
        isLecture=data.get("isLecture"),
    )
    return template


def extract_classrooms(str_list: list):
    """
    Extracts classrooms (including "ДОТ") and returns remaining list elements.

    Returns 'classrooms' and 'str_list_no_classrooms'.
    """
    str_list_saved = str_list.copy()
    number_regex = r"\d+"
    numbers = []
    fixed_numbers = []

    for element in str_list:
        # Проверка на пустые элементы
        if not element:
            continue

        # Если элемент содержит дробь или символы-разделители, добавляем его в fixed_numbers
        if "/" in element or ":" in element or ";" in element:
            fixed_numbers.append(element)

        # Если элемент не содержит дробь, но является числом, добавляем в numbers
        elif re.match(number_regex, element) and element not in ["1C", "1С"]:
            numbers.append(element)

        # Если элемент равен "ДОТ", добавляем его в numbers
        elif element.upper() == "ДОТ":
            numbers.append(element)

    # Удаление найденных кабинетов из исходного списка
    for num in numbers + fixed_numbers:
        str_list_saved.remove(num)

    # Если есть дробные числа, объединяем их с обычными числами
    if fixed_numbers and numbers:
        fixed_numbers = ["/".join(numbers + fixed_numbers)]
        numbers = fixed_numbers
    else:
        numbers += fixed_numbers

    return {"classrooms": numbers, "str_list_no_classrooms": str_list_saved}


def standardize_names(s):
    if s != "" and s is not None:
        s = s.replace(",", "")

        s = s.strip()
        # Замена точек и пробелов на символ ';'
        s = re.sub(r"[. ]", ";", s)
        while ";" in s:
            s = s.replace(";;", " ").replace(";", " ")

        s = s.strip()
        buff = list(s)
        buff[-2] = "."
        s = "".join(buff)

        # Если последний символ не точка, добавить точку
        if s[-1] != ".":
            s += "."
    return s


def split_number_and_surname(arr):
    """Обработка строк вида '226Иванова' с исключением для '1С:Предприятие 8'."""
    result = []
    i = 0
    while i < len(arr):
        # Проверяем, являются ли текущий и следующий элементы частью '1С:Предприятие 8'
        if i < len(arr) - 1 and arr[i] == "1С:Предприятие" and arr[i + 1] == "8":
            result.append("1С:Предприятие 8")
            i += 2  # Пропускаем следующий элемент
            continue

        # Обработка остальных элементов
        match = re.match(r"(\d+)([A-Za-zА-Яа-яЁё]+)", arr[i])
        if match:
            # Не разбиваем, если текстовая часть состоит из одной буквы
            if len(match.group(2)) == 1:
                result.append(arr[i])
            else:
                result.append(match.group(1))  # Число
                result.append(match.group(2))  # Слово
        else:
            result.append(arr[i])

        i += 1
    return result

