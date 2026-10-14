"""Генерирует клиентов, их телефоны и автомобили:
    data/client.csv, data/client_phone.csv, data/automobile.csv

Запуск из любого места:
    python import/create_clients.py
    python import/create_clients.py --clients 300 --multi 150 --no-cars 15 --null-middle 24
    python import/create_clients.py --format csv --auto-format json

Распределение автомобилей по клиентам задаётся точно (а не случайно):
    --no-cars   сколько клиентов без автомобилей (для запросов «нет связанных записей»)
    --multi     сколько клиентов с двумя и более автомобилями (из них 80% по 2, 15% по 3, 5% по 4)
    остальные клиенты владеют одним автомобилем.

Автомобили привязываются к model_id из каталога (create_catalog.py), поэтому
таблицу Model нужно загрузить раньше Automobile.
VIN синтетические: 17 символов без I, O, Q, с корректной контрольной цифрой.
Телефоны случайные и не принадлежат реальным людям (совпадение возможно чисто статистически).
"""
import argparse
import csv
import json
import random
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from create_catalog import MODELS  # noqa: E402
from create_staff import FEMALE_NAMES, MALE_NAMES, PATRONYMICS  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
SEED = 42

MALE_SHARE = 0.7  # доля мужчин среди клиентов
BRAND_WEIGHTS = {"BMW": 0.34, "Mercedes-Benz": 0.30, "Audi": 0.24, "Porsche": 0.12}

SURNAMES_M = """
Иванов Смирнов Кузнецов Попов Васильев Петров Соколов Михайлов Новиков Фёдоров Морозов Волков
Алексеев Лебедев Семёнов Егоров Павлов Козлов Степанов Николаев Орлов Андреев Макаров Никитин
Захаров Зайцев Соловьёв Борисов Яковлев Григорьев Романов Воробьёв Сергеев Кузьмин Фролов
Александров Дмитриев Королёв Гусев Киселёв Ильин Максимов Поляков Сорокин Виноградов Ковалёв
Белов Медведев Антонов Тарасов Жуков Баранов Филиппов Комаров Давыдов Беляев Герасимов Богданов
Осипов Сидоров Матвеев Титов Марков Миронов Крылов Куликов Карпов Власов Мельников Денисов
Гаврилов Тихонов Казаков Афанасьев Данилов Савельев Тимофеев Фомин Чернов Абрамов Мартынов
Ефимов Федотов Щербаков Назаров Калинин Исаев Чернышёв Быков Маслов Родионов Коновалов Лазарев
Воронин Климов Филатов Пономарёв Голубев Кудрявцев Прохоров Наумов Потапов Журавлёв Овчинников
Трофимов Леонов Соболев Ермаков Колесников Гончаров Емельянов Никифоров Грачёв Котов Гришин
Ефремов Архипов Громов Кириллов Малышев Панов Моисеев Румянцев Акимов Кондратьев Бирюков
Горбунов Анисимов Еремин Тихомиров Галкин Лукьянов Михеев Скворцов Юдин Белоусов Нестеров
Симонов Прокофьев Харитонов Князев Цветков Левин Митрофанов Воронов Аксёнов Мальцев Логинов
Горшков Савин Краснов Майоров Демидов Елисеев Рыбаков Сафонов Плотников Демин Хохлов Фадеев
Молчанов Игнатов Литвинов Ершов Ушаков Дементьев Рябов Мухин Калашников Леонтьев Лобанов
Ковальский Дубровский Красовский Белинский Волконский
""".split()

EXTRA_MALE = ["Вячеслав", "Леонид", "Тимур", "Ильдар", "Марк", "Матвей", "Данил", "Фёдор", "Всеволод"]
EXTRA_FEMALE = ["Валерия", "Полина", "Ксения", "Вера", "Надежда", "Кристина", "Алёна", "Оксана", "Людмила", "Галина"]

# годы выпуска модели (приблизительно) — нужны для 10-го символа VIN
MODEL_YEARS = {
    "E34": (1988, 1996), "E46": (1998, 2006), "E60": (2003, 2010), "F10": (2010, 2016),
    "F90": (2017, 2023), "G30": (2016, 2023), "G90": (2024, 2025), "G42": (2021, 2025),
    "E90": (2005, 2012), "G20": (2018, 2025), "G80": (2021, 2025), "G82": (2021, 2025),
    "F82": (2014, 2020),
    "W212": (2009, 2016), "W213": (2016, 2023), "W221": (2005, 2013), "W222": (2013, 2020),
    "W223": (2020, 2025), "C292": (2015, 2019), "W205": (2014, 2021), "W206": (2021, 2025),
    "A6C7": (2011, 2018), "A6C8": (2018, 2025), "A4B6": (2000, 2005), "A4B7": (2004, 2008),
    "A4B8": (2007, 2015), "A4B9": (2015, 2025),
    "991CARR": (2011, 2019), "991GTS": (2014, 2019), "991TARGA": (2014, 2019),
    "991TARGAS": (2014, 2019), "991TURBOS": (2013, 2019), "991GT3RS": (2015, 2019),
    "991GT2RS": (2017, 2018), "992CARR": (2019, 2025), "992TARGA": (2020, 2025),
    "992TURBOS": (2020, 2025), "992GT3RS": (2022, 2025),
}

# ---------------------------------------------------------------- VIN
VIN_ALPHABET = "ABCDEFGHJKLMNPRSTUVWXYZ0123456789"  # без I, O, Q
YEAR_CODES = "ABCDEFGHJKLMNPRSTVWXY123456789"       # 30 лет, начиная с 1980 / 2010
PLANT_CODES = {"BMW": "ACDEFGHJ", "Mercedes-Benz": "ABCFJKL", "Audi": "ABCDEFG", "Porsche": "SLN"}
TRANSLIT = {c: v for c, v in zip("ABCDEFGH", range(1, 9))}
TRANSLIT.update({"J": 1, "K": 2, "L": 3, "M": 4, "N": 5, "P": 7, "R": 9, "S": 2, "T": 3,
                 "U": 4, "V": 5, "W": 6, "X": 7, "Y": 8, "Z": 9})
WEIGHTS = [8, 7, 6, 5, 4, 3, 2, 10, 0, 9, 8, 7, 6, 5, 4, 3, 2]


def check_digit(vin16):
    """vin16: 17 символов, где 9-й (индекс 8) — заглушка. Возвращает контрольный символ."""
    total = 0
    for ch, w in zip(vin16, WEIGHTS):
        total += (int(ch) if ch.isdigit() else TRANSLIT[ch]) * w
    r = total % 11
    return "X" if r == 10 else str(r)


def make_vin(rng, brand, model_name, code, used):
    while True:
        if brand == "BMW":
            wmi = "WBS" if model_name.startswith("M") else "WBA"
        elif brand == "Mercedes-Benz":
            wmi = "WDC" if code == "C292" else "WDD"
        elif brand == "Audi":
            wmi = "WAU"
        else:
            wmi = "WP0"
        year = rng.randint(*MODEL_YEARS[code])
        body = "".join(rng.choice(VIN_ALPHABET) for _ in range(5))
        plant = rng.choice(PLANT_CODES[brand])
        serial = "".join(rng.choice("0123456789") for _ in range(6))
        vin = wmi + body + "0" + YEAR_CODES[(year - 1980) % 30] + plant + serial
        vin = vin[:8] + check_digit(vin) + vin[9:]
        if vin not in used:
            used.add(vin)
            return vin


# ---------------------------------------------------------------- госномера
PLATE_LETTERS = "АВЕКМНОРСТУХ"  # только буквы, разрешённые на российских номерах (кириллица)
REGIONS = (["77"] * 6 + ["177"] * 3 + ["777"] * 3 + ["97", "97", "99", "199", "197", "799",
           "50", "150", "90", "190", "750", "78", "178", "47", "23", "93", "163", "52",
           "16", "116", "72", "66", "196"])


def make_plate(rng, used):
    while True:
        plate = "{}{:03d}{}{} {}".format(
            rng.choice(PLATE_LETTERS), rng.randint(1, 999),
            rng.choice(PLATE_LETTERS), rng.choice(PLATE_LETTERS), rng.choice(REGIONS))
        if plate not in used:
            used.add(plate)
            return plate


# ---------------------------------------------------------------- люди и телефоны
def female_form(surname):
    if surname.endswith("ский"):
        return surname[:-4] + "ская"
    return surname + "а"


def make_clients(rng, n, null_middle):
    male_names = MALE_NAMES + EXTRA_MALE
    female_names = FEMALE_NAMES + EXTRA_FEMALE
    fathers = list(PATRONYMICS)
    seen, clients = set(), []
    for _ in range(n):
        female = rng.random() >= MALE_SHARE
        while True:
            surname = rng.choice(SURNAMES_M)
            first = rng.choice(female_names if female else male_names)
            middle = PATRONYMICS[rng.choice(fathers)][1 if female else 0]
            last = female_form(surname) if female else surname
            if (last, first, middle) not in seen:
                seen.add((last, first, middle))
                break
        clients.append([last, first, middle])
    for idx in rng.sample(range(n), null_middle):
        clients[idx][2] = None
    return clients


def make_phones(rng, n):
    used, rows = set(), []
    for cid in range(1, n + 1):
        count = rng.choices([1, 2, 3], weights=[60, 30, 10])[0]
        for _ in range(count):
            while True:
                num = "+7 9{:02d} {:03d}-{:02d}-{:02d}".format(
                    rng.randint(0, 99), rng.randint(0, 999), rng.randint(0, 99), rng.randint(0, 99))
                if num not in used:
                    used.add(num)
                    break
            rows.append({"client_id": cid, "phone": num})
    return rows


# ---------------------------------------------------------------- автомобили
def cars_per_client(rng, n, no_cars, multi):
    one = n - no_cars - multi
    assert one >= 0, "no-cars + multi больше числа клиентов"
    n4 = round(multi * 0.05)
    n3 = round(multi * 0.15)
    n2 = multi - n3 - n4
    counts = [0] * no_cars + [1] * one + [2] * n2 + [3] * n3 + [4] * n4
    rng.shuffle(counts)
    return counts


def make_cars(rng, counts):
    models_by_brand = {}
    for model_id, (code, brand, name, *_rest) in enumerate(MODELS, start=1):
        models_by_brand.setdefault(brand, []).append((model_id, code, name))
    brands = list(BRAND_WEIGHTS)
    weights = [BRAND_WEIGHTS[b] for b in brands]

    used_vins, used_plates, cars = set(), set(), []
    for client_id, k in enumerate(counts, start=1):
        for _ in range(k):
            brand = rng.choices(brands, weights=weights)[0]
            model_id, code, name = rng.choice(models_by_brand[brand])
            cars.append({
                "vin": make_vin(rng, brand, name, code, used_vins),
                "gos_number": make_plate(rng, used_plates),
                "client_id": client_id,
                "model_id": model_id,
            })
    return cars


# ---------------------------------------------------------------- запись
def write(path, fields, rows, fmt):
    if fmt == "csv":
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(rows)  # None -> пустое поле
    else:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False, indent=2)


def main():
    p = argparse.ArgumentParser(description="Создать данные: Client, Client_Phone, Automobile")
    p.add_argument("--clients", type=int, default=200)
    p.add_argument("--multi", type=int, default=100, help="клиентов с 2+ автомобилями")
    p.add_argument("--no-cars", type=int, default=10, help="клиентов без автомобилей")
    p.add_argument("--null-middle", type=int, default=16, help="клиентов без отчества (NULL)")
    p.add_argument("--format", choices=["csv", "json"], default="csv")
    p.add_argument("--phone-format", choices=["csv", "json"])
    p.add_argument("--auto-format", choices=["csv", "json"])
    p.add_argument("--seed", type=int, default=SEED)
    a = p.parse_args()
    phone_fmt = a.phone_format or a.format
    auto_fmt = a.auto_format or a.format

    rng = random.Random(a.seed)
    people = make_clients(rng, a.clients, a.null_middle)
    clients = [{"client_id": i, "last_name": ln, "first_name": fn, "middle_name": mn}
               for i, (ln, fn, mn) in enumerate(people, start=1)]
    phones = make_phones(rng, a.clients)
    counts = cars_per_client(rng, a.clients, a.no_cars, a.multi)
    cars = make_cars(rng, counts)

    DATA_DIR.mkdir(exist_ok=True)
    write(DATA_DIR / f"client.{a.format}",
          ["client_id", "last_name", "first_name", "middle_name"], clients, a.format)
    write(DATA_DIR / f"client_phone.{phone_fmt}", ["client_id", "phone"], phones, phone_fmt)
    write(DATA_DIR / f"automobile.{auto_fmt}",
          ["vin", "gos_number", "client_id", "model_id"], cars, auto_fmt)

    dist = Counter(counts)
    print(f"client.{a.format}: {len(clients)} строк, без отчества (NULL): "
          f"{sum(1 for c in clients if c['middle_name'] is None)}")
    print(f"client_phone.{phone_fmt}: {len(phones)} строк")
    print(f"automobile.{auto_fmt}: {len(cars)} строк")
    print("Автомобилей на клиента:", ", ".join(f"{k}: {dist[k]} кл." for k in sorted(dist)),
          f"| с 2+ авто: {sum(v for k, v in dist.items() if k >= 2)}")


if __name__ == "__main__":
    main()
