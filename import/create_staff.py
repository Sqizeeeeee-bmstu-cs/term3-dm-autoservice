"""Генерирует сотрудников автосервиса: data/master.csv и data/administrator.csv.

Поля обеих таблиц: <role>_id, last_name, first_name, middle_name.
У части сотрудников отчество не указано (NULL): в CSV это пустое поле, в JSON null.

Запуск из любого места:
    python import/create_staff.py
    python import/create_staff.py --format json --admin-format csv
"""
import argparse
import csv
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
SEED = 42

N_MASTERS = 30
N_ADMINS = 6
NULL_MIDDLE_MASTERS = 3   # у скольких мастеров отчество = NULL
NULL_MIDDLE_ADMINS = 1    # у скольких администраторов отчество = NULL

# фамилии: (мужская, женская)
SURNAMES = [
    ("Иванов", "Иванова"), ("Смирнов", "Смирнова"), ("Кузнецов", "Кузнецова"),
    ("Попов", "Попова"), ("Соколов", "Соколова"), ("Лебедев", "Лебедева"),
    ("Козлов", "Козлова"), ("Новиков", "Новикова"), ("Морозов", "Морозова"),
    ("Петров", "Петрова"), ("Волков", "Волкова"), ("Соловьёв", "Соловьёва"),
    ("Васильев", "Васильева"), ("Зайцев", "Зайцева"), ("Павлов", "Павлова"),
    ("Семёнов", "Семёнова"), ("Голубев", "Голубева"), ("Виноградов", "Виноградова"),
    ("Богданов", "Богданова"), ("Воробьёв", "Воробьёва"), ("Фёдоров", "Фёдорова"),
    ("Михайлов", "Михайлова"), ("Беляев", "Беляева"), ("Тарасов", "Тарасова"),
    ("Белов", "Белова"), ("Комаров", "Комарова"), ("Орлов", "Орлова"),
    ("Киселёв", "Киселёва"), ("Макаров", "Макарова"), ("Андреев", "Андреева"),
    ("Ковалёв", "Ковалёва"), ("Ильин", "Ильина"), ("Гусев", "Гусева"),
    ("Титов", "Титова"), ("Кузьмин", "Кузьмина"), ("Кудрявцев", "Кудрявцева"),
    ("Баранов", "Баранова"), ("Куликов", "Куликова"), ("Алексеев", "Алексеева"),
    ("Степанов", "Степанова"),
]

MALE_NAMES = [
    "Александр", "Дмитрий", "Сергей", "Андрей", "Алексей", "Михаил", "Иван",
    "Максим", "Евгений", "Артём", "Николай", "Денис", "Павел", "Роман",
    "Владимир", "Игорь", "Олег", "Кирилл", "Виталий", "Антон", "Георгий",
    "Руслан", "Станислав", "Юрий", "Константин",
]
FEMALE_NAMES = [
    "Анна", "Мария", "Елена", "Ольга", "Наталья", "Екатерина", "Татьяна",
    "Ирина", "Юлия", "Светлана", "Анастасия", "Дарья", "Виктория", "Алина",
]

# имя отца -> (отчество мужское, отчество женское)
PATRONYMICS = {
    "Александр": ("Александрович", "Александровна"),
    "Сергей": ("Сергеевич", "Сергеевна"),
    "Андрей": ("Андреевич", "Андреевна"),
    "Алексей": ("Алексеевич", "Алексеевна"),
    "Михаил": ("Михайлович", "Михайловна"),
    "Иван": ("Иванович", "Ивановна"),
    "Николай": ("Николаевич", "Николаевна"),
    "Дмитрий": ("Дмитриевич", "Дмитриевна"),
    "Владимир": ("Владимирович", "Владимировна"),
    "Игорь": ("Игоревич", "Игоревна"),
    "Олег": ("Олегович", "Олеговна"),
    "Павел": ("Павлович", "Павловна"),
    "Виктор": ("Викторович", "Викторовна"),
    "Юрий": ("Юрьевич", "Юрьевна"),
    "Анатолий": ("Анатольевич", "Анатольевна"),
    "Геннадий": ("Геннадьевич", "Геннадьевна"),
    "Валерий": ("Валерьевич", "Валерьевна"),
    "Григорий": ("Григорьевич", "Григорьевна"),
    "Евгений": ("Евгеньевич", "Евгеньевна"),
    "Борис": ("Борисович", "Борисовна"),
}


def make_people(rng, count, surnames, names, female, null_middle):
    """Возвращает список (фамилия, имя, отчество или None) без повторов."""
    people, seen = [], set()
    fathers = list(PATRONYMICS)
    for surname in surnames[:count]:
        while True:
            first = rng.choice(names)
            middle = PATRONYMICS[rng.choice(fathers)][1 if female else 0]
            key = (surname, first, middle)
            if key not in seen:
                seen.add(key)
                break
        people.append([surname, first, middle])
    for idx in rng.sample(range(count), null_middle):
        people[idx][2] = None
    return [tuple(p) for p in people]


def build(seed=SEED):
    rng = random.Random(seed)
    pool = SURNAMES[:]
    rng.shuffle(pool)
    master_surnames = [m for m, _ in pool[:N_MASTERS]]
    admin_surnames = [f for _, f in pool[N_MASTERS:N_MASTERS + N_ADMINS]]

    masters = make_people(rng, N_MASTERS, master_surnames, MALE_NAMES, False, NULL_MIDDLE_MASTERS)
    admins = make_people(rng, N_ADMINS, admin_surnames, FEMALE_NAMES, True, NULL_MIDDLE_ADMINS)

    def rows(people, id_field):
        return [
            {id_field: i, "last_name": ln, "first_name": fn, "middle_name": mn}
            for i, (ln, fn, mn) in enumerate(people, start=1)
        ]

    return rows(masters, "master_id"), rows(admins, "admin_id")


def write(path: Path, fields, rows, fmt):
    if fmt == "csv":
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(rows)  # None записывается как пустое поле
    else:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False, indent=2)


def main():
    parser = argparse.ArgumentParser(description="Создать файлы данных: Master и Administrator")
    parser.add_argument("--format", choices=["csv", "json"], default="csv",
                        help="формат для мастеров (и администраторов, если не задан --admin-format)")
    parser.add_argument("--admin-format", choices=["csv", "json"],
                        help="формат для администраторов")
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args()
    admin_fmt = args.admin_format or args.format

    masters, admins = build(args.seed)
    DATA_DIR.mkdir(exist_ok=True)
    fields = ["last_name", "first_name", "middle_name"]
    for filename, id_field, rows, fmt in (
        (f"master.{args.format}", "master_id", masters, args.format),
        (f"administrator.{admin_fmt}", "admin_id", admins, admin_fmt),
    ):
        write(DATA_DIR / filename, [id_field] + fields, rows, fmt)
        nulls = sum(1 for r in rows if r["middle_name"] is None)
        print(f"{filename}: {len(rows)} строк, без отчества (NULL): {nulls}")


if __name__ == "__main__":
    main()
    