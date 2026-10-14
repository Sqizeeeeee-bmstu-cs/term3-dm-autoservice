"""Генерирует заказ-наряды и всё, что к ним привязано:
    data/work_order.csv, data/order_service.csv, data/part_position.csv, data/status_change.csv

Запуск из любого места (после того как созданы остальные файлы в data/):
    python import/create_orders.py
    python import/create_orders.py --orders 5000 --years 3 --end-date 2026-10-14
    python import/create_orders.py --format csv --os-format json --sc-format json

Скрипт читает уже созданные файлы (automobile, service, model_part_compatibility, master,
administrator, csv или json), поэтому сначала запусти create_catalog.py, create_services.py,
create_staff.py и create_clients.py.

Что учитывается:
  - заказ принадлежит существующему автомобилю; у одних машин заказов много, у других мало;
  - услуги и запчасти согласованы: к услуге «Замена свечей (6 цил.)» ставятся свечи именно того
    двигателя этого автомобиля, который совместим с его моделью (двигатель фиксирован за VIN);
  - количество в Order_Service подходит под услуги «1 шт.» и «1 ось»;
  - статус зависит от возраста заказа: старые почти все «выдан», свежие чаще «в работе»;
  - история Status_Change заканчивается тем же статусом, который стоит в Work_Order;
  - NULL: planned_date и malfunction у части заказов, end_date у незавершённых и отменённых.
Порядок загрузки: work_order, order_service, part_position, status_change.
"""
import argparse
import csv
import json
import random
import re
import sys
from collections import Counter
from datetime import date, datetime, time, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from create_catalog import ENGINES  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
SEED = 42
DEFAULT_END_DATE = "2026-10-14"

ROBOT_FAMILIES = {"BMWDCT", "AUDI_S7", "PDK"}
CALIPER_POS = ["FL", "FR", "RL", "RR"]

# вес популярности услуги: первое совпадение подстроки; всё остальное имеет вес 1
SERVICE_WEIGHTS = [
    ("Компьютерная диагностика", 10), ("Диагностика ходовой", 4), ("Диагностика двигателя", 4),
    ("Диагностика тормозной", 3), ("Диагностика", 2), ("Проверка автомобиля", 1.5),
    ("Замена моторного масла", 12), ("ТО-1", 8), ("ТО-2", 5),
    ("Замена масла в АКПП (частичная", 3), ("Замена масла в АКПП (полная", 2),
    ("Замена масла в роботизированной", 3), ("Замена антифриза", 3),
    ("Замена воздушного фильтра", 4), ("Замена салонного фильтра", 5),
    ("Замена топливного фильтра", 2), ("Замена тормозных колодок", 10),
    ("Замена тормозных дисков", 5), ("Замена карбон-керамических", 2),
    ("Замена тормозного суппорта", 2), ("Замена датчика ABS", 2), ("Прокачка тормозной", 3),
    ("Замена тормозной жидкости", 4), ("Развал-схождение", 5), ("Шиномонтаж", 5),
    ("Балансировка", 4), ("Замена свечей", 4), ("Замена катушек", 2), ("Замена форсунок", 1.5),
    ("Ультразвуковая чистка", 2), ("Замена ремня или цепи ГРМ", 2),
    ("Замена амортизатора", 3), ("Замена пружины", 1), ("Замена рычага", 2),
    ("Замена стойки стабилизатора", 3), ("Замена шаровой", 2), ("Замена сайлентблока", 2),
    ("Замена подшипника ступицы", 2), ("Замена приводного ремня", 2), ("Замена термостата", 1.5),
    ("Замена водяного насоса", 1.5), ("Замена радиатора", 1), ("Замена аккумулятора", 2.5),
    ("Заправка кондиционера", 2.5), ("Диагностика и ремонт кондиционера", 1.5),
    ("Кодирование", 1.5), ("Прошивка", 0.8), ("Замена ТНВД", 0.7),
    ("Замена топливного насоса", 1), ("Замена турбины", 0.8), ("Замена нагнетателя", 0.3),
    ("Замена коробки передач", 0.4), ("Снятие и установка двигателя", 0.2),
    ("Установка даунпайпа", 0.6), ("Установка cat-back", 0.6),
    ("Установка полной выхлопной", 0.4), ("Ремонт выхлопной", 1),
]

HEAVY_WORDS = ("Снятие и установка двигателя", "коробки передач", "турбины", "нагнетателя",
               "ТНВД", "Прошивка", "ГРМ")

# жалобы клиентов по группам: (ключевые слова в названии первой услуги, варианты)
COMPLAINTS = [
    (("ТО-", "моторного масла", "фильтр"),
     ["Плановое техническое обслуживание", "Пробег до ТО, обслуживание по регламенту",
      "Сезонное обслуживание", "Подошёл срок замены масла"]),
    (("тормоз", "колодок", "дисков", "суппорт", "ABS"),
     ["Скрип при торможении", "Вибрация руля при торможении", "Горит индикатор ABS",
      "Увеличился тормозной путь", "Педаль тормоза стала мягкой"]),
    (("подвеск", "амортизатор", "рычаг", "стойк", "шарово", "сайлент", "ступиц", "Развал",
      "пружин"),
     ["Стук в передней подвеске", "Стук при проезде неровностей", "Автомобиль уводит в сторону",
      "Гул при движении", "Неравномерный износ шин"]),
    (("свеч", "катуш", "форсун", "ТНВД", "топлив"),
     ["Горит Check Engine", "Троит двигатель на холостых", "Плавающие обороты",
      "Затруднённый запуск", "Повышенный расход топлива"]),
    (("турбин", "нагнетател", "Прошивка"),
     ["Потеря мощности при разгоне", "Свист при наборе скорости", "Дым из выхлопной трубы"]),
    (("коробк", "АКПП", "PDK"),
     ["Рывки при переключении передач", "Пинки при начале движения",
      "Ошибка коробки передач на панели", "Задержка при включении передачи"]),
    (("выхлоп", "даунпайп", "cat-back"),
     ["Гул выхлопной системы", "Хочу более спортивный звук выхлопа", "Течь выхлопной системы"]),
    (("кондиционер",),
     ["Не охлаждает кондиционер", "Неприятный запах из дефлекторов"]),
    (("аккумулятор", "Кодирование"),
     ["Не заводится утром", "Быстро садится аккумулятор", "Ошибки электронных блоков"]),
    (("антифриз", "радиатор", "термостат", "насос", "помп"),
     ["Перегрев двигателя", "Течь охлаждающей жидкости"]),
]
GENERAL_COMPLAINTS = ["Посторонний шум при движении", "Диагностика по ошибке на панели",
                      "Осмотр перед дальней поездкой", "Вибрация при движении",
                      "Проверка после покупки автомобиля"]


# ---------------------------------------------------------------- чтение файлов
def load(name, hint):
    for ext in ("csv", "json"):
        p = DATA_DIR / f"{name}.{ext}"
        if p.exists():
            if ext == "csv":
                with open(p, newline="", encoding="utf-8-sig") as f:
                    return list(csv.DictReader(f))
            with open(p, encoding="utf-8") as f:
                return json.load(f)
    sys.exit(f"Не найден data/{name}.csv или .json. Сначала запусти {hint}")


# ---------------------------------------------------------------- услуги и запчасти
def service_weight(name):
    for key, w in SERVICE_WEIGHTS:
        if key in name:
            return w
    return 1.0


def service_group(name):
    if name.startswith("Замена моторного масла") or name.startswith("ТО-"):
        return "maint"
    if name.startswith(("Диагностика", "Компьютерная диагностика", "Проверка автомобиля")):
        return "diag"
    return None


def service_qty(name, rng):
    if "турбины" in name:
        return 1
    if "1 ось" in name:
        return rng.choice([1, 1, 1, 1, 2])
    if "ABS" in name and "1 шт." in name:
        return rng.choice([1, 1, 2, 2, 4])
    if "суппорт" in name and "1 шт." in name:
        return rng.choice([1, 1, 1, 2, 2])
    if "1 шт." in name:
        return rng.choice([1, 1, 2, 2, 4])
    return 1


def plan_parts(name, ctx, qty, rng):
    """Список (артикул, количество) для услуги или None, если она не подходит этой машине."""
    C, e, code, cyl = ctx["compat"], ctx["engine"], ctx["code"], ctx["cyl"]
    m = re.search(r"\((\d+) цил\.\)", name)
    if m and int(m.group(1)) != cyl:
        return None

    def one(prefix, key=None):
        art = f"{prefix}-{key or e}"
        return [(art, 1)] if art in C else None

    def many(*lists):
        return [x for lst in lists if lst for x in lst]

    if name.startswith("Замена моторного масла"):
        return one("OILKIT")
    if name.startswith("ТО-1"):
        return many(one("OILKIT"), one("AFLT"), one("CAB", code))
    if name.startswith("ТО-2"):
        return many(one("OILKIT"), one("AFLT"), one("CAB", code), one("FFLT"), one("PLUG"))
    if name.startswith("Замена масла в"):
        goil = sorted(a for a in C if a.startswith("GOIL-"))
        if not goil:
            return None
        robot = goil[0].split("-", 1)[1] in ROBOT_FAMILIES
        if ("роботизированной" in name) != robot:
            return None
        return [(goil[0], 2 if "полная" in name else 1)]
    if name == "Замена антифриза":
        opts = sorted(a for a in C if a.startswith("COOL-") and a.endswith("-5L"))
        return [(opts[0], rng.choice([1, 1, 2]))] if opts else None
    if name == "Замена воздушного фильтра":
        return one("AFLT")
    if name == "Замена салонного фильтра":
        return one("CAB", code)
    if name == "Замена топливного фильтра":
        return one("FFLT")
    if name == "Замена ТНВД":
        return one("HPFP")
    if name == "Замена топливного насоса":
        return one("FPMP")
    if name.startswith("Замена турбины"):
        return one("TRB")
    if name.startswith("Замена нагнетателя"):
        return one("SC")
    if name.startswith("Замена коробки передач"):
        return one("GBX", code)
    if name.startswith("Замена карбон-керамических"):
        if f"DSK-F-CC-{code}" not in C:
            return None
        axles = ["F", "R"] if qty >= 2 else [rng.choice("FR")]
        return [(f"DSK-{ax}-CC-{code}", 2) for ax in axles]
    if name.startswith("Замена тормозных дисков"):
        axles = ["F", "R"] if qty >= 2 else [rng.choice("FR")]
        return [(f"DSK-{ax}-{code}", 2) for ax in axles]
    if name.startswith("Замена тормозного суппорта"):
        return [(f"CLP-{p}-{code}", 1) for p in rng.sample(CALIPER_POS, min(qty, 4))]
    if name.startswith("Замена датчика ABS"):
        return [(f"ABS-{p}-{code}", 1) for p in rng.sample(CALIPER_POS, min(qty, 4))]
    if name.startswith("Установка даунпайпа"):
        return one("EXH-DP", code)
    if name.startswith("Установка cat-back"):
        return one("EXH-CB", code)
    if name.startswith("Установка полной выхлопной"):
        return one("EXH-FS", code)
    if name.startswith("Замена свечей"):
        return one("PLUG")
    if name.startswith("Замена катушек"):
        return one("COIL")
    if name.startswith("Замена форсунок"):
        return one("INJ")
    if name.startswith("Снятие и установка двигателя"):
        return one("ENG")
    return []


def pick_services(services, weights, ctx, n, rng, need_parts):
    for _attempt in range(25):
        w = list(weights)
        chosen, groups = [], set()
        while len(chosen) < n and sum(w) > 0:
            i = rng.choices(range(len(services)), weights=w)[0]
            w[i] = 0
            name = services[i]["name"]
            g = service_group(name)
            if g and g in groups:
                continue
            qty = service_qty(name, rng)
            parts = plan_parts(name, ctx, qty, rng)
            if parts is None:
                continue
            if g:
                groups.add(g)
            chosen.append((services[i], qty, parts))
        if chosen and (not need_parts or any(p for _s, _q, p in chosen)):
            return chosen
    return chosen


def complaint(first_service, rng):
    for words, options in COMPLAINTS:
        if any(w in first_service for w in words):
            return rng.choice(options)
    return rng.choice(GENERAL_COMPLAINTS)


# ---------------------------------------------------------------- статусы и даты
def draw_status(age, rng):
    if age >= 30:
        table = [("выдан", .92), ("отменён", .07), ("готов", .01)]
    elif age >= 10:
        table = [("выдан", .75), ("готов", .08), ("отменён", .06), ("ожидает запчасти", .06),
                 ("в работе", .05)]
    elif age >= 3:
        table = [("выдан", .45), ("готов", .17), ("в работе", .18), ("ожидает запчасти", .12),
                 ("отменён", .08)]
    else:
        table = [("в работе", .45), ("ожидает запчасти", .20), ("готов", .20), ("выдан", .10),
                 ("отменён", .05)]
    return rng.choices([s for s, _ in table], weights=[p for _, p in table])[0]


def draw_duration(heavy, rng):
    dur = rng.choices([0, 1, 2, rng.randint(3, 5), rng.randint(6, 14)],
                      weights=[35, 25, 15, 15, 10])[0]
    return dur + (rng.randint(4, 18) if heavy else 0)


def build_events(rng, status, start, dur, age, today):
    """Цепочка статусов [(статус, дата)] и итоговые end_date (или None)."""
    d = timedelta
    events = [("в работе", start)]
    end_date = None
    if status == "ожидает запчасти":
        events.append((status, start + d(days=rng.randint(0, min(3, age)))))
    elif status == "в работе":
        if age >= 3 and rng.random() < 0.2:
            w = rng.randint(0, 1)
            events.append(("ожидает запчасти", start + d(days=w)))
            events.append(("в работе", start + d(days=min(age, w + rng.randint(1, 2)))))
    elif status == "отменён":
        cancel_off = min(rng.randint(0, 3), age)
        if cancel_off >= 2 and rng.random() < 0.2:
            events.append(("ожидает запчасти", start + d(days=1)))
        events.append((status, start + d(days=cancel_off)))
    else:  # готов / выдан
        dur = min(dur, age)
        k = min(rng.choice([0, 0, 0, 1, 2]), dur) if status == "выдан" else 0
        ready_off = dur - k
        if ready_off >= 2 and rng.random() < 0.25:
            w = rng.randint(0, ready_off - 2)
            b = rng.randint(w + 1, ready_off - 1)
            events.append(("ожидает запчасти", start + d(days=w)))
            events.append(("в работе", start + d(days=b)))
        events.append(("готов", start + d(days=ready_off)))
        end_date = start + d(days=dur)
        if status == "выдан":
            events.append(("выдан", end_date))
    return events, end_date


def stamp(rng, events, today):
    by_date = {}
    for idx, (_st, dt) in enumerate(events):
        by_date.setdefault(dt, []).append(idx)
    times = {}
    for dt, idxs in by_date.items():
        lo, hi = 8 * 60 + 30, (17 * 60 if dt == today else 19 * 60)
        width = (hi - lo) / len(idxs)
        for j, idx in enumerate(idxs):
            minute = int(lo + width * j + rng.random() * width * 0.95)
            times[idx] = datetime.combine(dt, time(minute // 60, minute % 60, rng.randint(0, 59)))
    return [(st, times[i]) for i, (st, _dt) in enumerate(events)]


# ---------------------------------------------------------------- генерация
def build(args):
    rng = random.Random(args.seed)
    today = date.fromisoformat(args.end_date)
    first_day = today.replace(year=today.year - args.years) + timedelta(days=1)

    cars = load("automobile", "create_clients.py")
    services = load("service", "create_services.py")
    compat_rows = load("model_part_compatibility", "create_catalog.py")
    masters = load("master", "create_staff.py")
    admins = load("administrator", "create_staff.py")

    compat = {}
    for r in compat_rows:
        compat.setdefault(int(r["model_id"]), set()).add(r["article"])
    for s in services:
        s["service_id"] = int(s["service_id"])
    svc_weights = [service_weight(s["name"]) for s in services]

    # --- даты заказов: будни, суббота реже, воскресенья нет, рост нагрузки к концу периода
    days = [first_day + timedelta(days=i) for i in range((today - first_day).days + 1)]
    day_w = []
    for i, dt in enumerate(days):
        wd = dt.weekday()
        base = 0.0 if wd == 6 else 0.35 if wd == 5 else 1.0
        day_w.append(base * (0.7 + 0.6 * i / len(days)))
    starts = sorted(rng.choices(days, weights=day_w, k=args.orders))

    car_w = [rng.lognormvariate(0, 0.6) for _ in cars]
    master_w = [rng.uniform(0.5, 1.5) for _ in masters]
    admin_w = [rng.uniform(0.7, 1.3) for _ in admins]

    engine_cache = {}
    work_orders, order_services, positions, changes = [], [], [], []
    for num, start in enumerate(starts, start=1):
        car = rng.choices(cars, weights=car_w)[0]
        vin, mid = car["vin"], int(car["model_id"])
        C = compat[mid]
        if vin not in engine_cache:
            engines = sorted(a[4:] for a in C if a.startswith("ENG-"))
            e = random.Random(f"{args.seed}-{vin}").choice(engines)
            code = next(a[4:] for a in C if a.startswith("GBX-"))
            engine_cache[vin] = (e, code)
        e, code = engine_cache[vin]
        ctx = {"compat": C, "engine": e, "code": code, "cyl": ENGINES[e][1]}

        age = (today - start).days
        status = draw_status(age, rng)
        n_serv = rng.choices([1, 2, 3, 4], weights=[40, 35, 18, 7])[0]
        chosen = pick_services(services, svc_weights, ctx, n_serv, rng,
                               need_parts=(status == "ожидает запчасти"))
        heavy = any(w in s["name"] for s, _q, _p in chosen for w in HEAVY_WORDS)
        dur = draw_duration(heavy, rng)

        events, end_date = build_events(rng, status, start, dur, age, today)
        planned = start + timedelta(days=max(0, dur + rng.choice([-1, 0, 0, 1, 2, 3])))

        for s, q, _p in chosen:
            order_services.append({"order_number": num, "service_id": s["service_id"], "quantity": q})

        pos = 0
        for _s, _q, parts in chosen:
            for art, qty in parts:
                pos += 1
                positions.append({"order_number": num, "position_number": pos,
                                  "article": art, "quantity": qty})
        # иногда та же запчасть встречается в заказе отдельной позицией (докупка)
        own = [p for p in positions if p["order_number"] == num]
        if own and rng.random() < 0.04:
            src = rng.choice(own)
            pos += 1
            positions.append({"order_number": num, "position_number": pos,
                              "article": src["article"], "quantity": 1})

        work_orders.append({
            "order_number": num,
            "vin": vin,
            "admin_id": int(rng.choices(admins, weights=admin_w)[0]["admin_id"]),
            "master_id": int(rng.choices(masters, weights=master_w)[0]["master_id"]),
            "status": status,
            "start_date": start.isoformat(),
            "planned_date": None if rng.random() < args.null_planned else planned.isoformat(),
            "end_date": end_date.isoformat() if end_date else None,
            "malfunction": None if rng.random() < args.null_malfunction
            else complaint(chosen[0][0]["name"] if chosen else "", rng),
        })

        for st, ts in stamp(rng, events, today):
            changes.append({"order_number": num, "status": st,
                            "changed_at": ts.strftime("%Y-%m-%d %H:%M:%S")})

    for i, ch in enumerate(changes, start=1):
        ch["change_id"] = i
    changes = [{"change_id": c["change_id"], "order_number": c["order_number"],
                "status": c["status"], "changed_at": c["changed_at"]} for c in changes]
    return work_orders, order_services, positions, changes


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
    p = argparse.ArgumentParser(description="Создать данные: Work_Order, Order_Service, Part_Position, Status_Change")
    p.add_argument("--orders", type=int, default=2000)
    p.add_argument("--years", type=int, default=3)
    p.add_argument("--end-date", default=DEFAULT_END_DATE, help="последний день периода YYYY-MM-DD")
    p.add_argument("--null-planned", type=float, default=0.08, help="доля заказов с planned_date = NULL")
    p.add_argument("--null-malfunction", type=float, default=0.10, help="доля заказов с malfunction = NULL")
    p.add_argument("--format", choices=["csv", "json"], default="csv")
    p.add_argument("--os-format", choices=["csv", "json"], help="формат order_service")
    p.add_argument("--pp-format", choices=["csv", "json"], help="формат part_position")
    p.add_argument("--sc-format", choices=["csv", "json"], help="формат status_change")
    p.add_argument("--seed", type=int, default=SEED)
    a = p.parse_args()

    wo, os_, pp, sc = build(a)
    DATA_DIR.mkdir(exist_ok=True)
    outputs = [
        ("work_order", ["order_number", "vin", "admin_id", "master_id", "status", "start_date",
                        "planned_date", "end_date", "malfunction"], wo, a.format),
        ("order_service", ["order_number", "service_id", "quantity"], os_, a.os_format or a.format),
        ("part_position", ["order_number", "position_number", "article", "quantity"], pp,
         a.pp_format or a.format),
        ("status_change", ["change_id", "order_number", "status", "changed_at"], sc,
         a.sc_format or a.format),
    ]
    for name, fields, rows, fmt in outputs:
        write(DATA_DIR / f"{name}.{fmt}", fields, rows, fmt)
        print(f"{name}.{fmt}: {len(rows)} строк")

    print("\nСтатусы заказов:", dict(Counter(r["status"] for r in wo)))
    print("NULL: planned_date =", sum(r["planned_date"] is None for r in wo),
          "| end_date =", sum(r["end_date"] is None for r in wo),
          "| malfunction =", sum(r["malfunction"] is None for r in wo))
    print("Период:", wo[0]["start_date"], "-", wo[-1]["start_date"])


if __name__ == "__main__":
    main()
