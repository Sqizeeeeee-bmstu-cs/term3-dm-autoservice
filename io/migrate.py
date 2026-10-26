"""Миграция структуры БД: добавляет в таблицу Part столбец category.

Категория запчасти берётся из префикса артикула (ENG-..., DSK-..., OILKIT-... и т.д.).
Если префикса нет в таблице соответствия, запчасть получает категорию «Прочее».

SQLite не умеет добавлять столбец с ограничениями (NOT NULL + CHECK) к существующей
таблице, поэтому выполняется типовая миграция через новую таблицу:
    1. создать Part_new со столбцом category;
    2. перенести данные из Part, вычислив category по префиксу артикула;
    3. удалить Part;
    4. переименовать Part_new в Part.

На Part ссылаются Model_Part_Compatibility (ON DELETE CASCADE) и Part_Position (RESTRICT),
поэтому на время перестройки внешние ключи отключаются, а перед фиксацией проверяются
через PRAGMA foreign_key_check. Всё выполняется в одной транзакции: при любой ошибке
база остаётся такой, какой была. Перед миграцией делается резервная копия
(backups/before-migration_<дата_время>/), вернуться к ней можно командой backup.py restore.

Запуск из любого места (соединение с базой в DBeaver лучше закрыть):
    python io/migrate.py
    python io/migrate.py --db db/autoservice.sqlite --no-backup

Скрипт можно запускать повторно: если столбец уже есть, он ничего не изменит.
Файл backup.py должен лежать в io/ или lab1/.
"""
import argparse
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

try:
    from backup import make_backup, row_counts
except ImportError:
    sys.exit("Не найден backup.py: положите его в io/ или lab1/")

DEFAULT_DB = ROOT / "db" / "autoservice.sqlite"
DEFAULT_BACKUPS = ROOT / "backups"
BACKUP_PREFIX = "before-migration_"

DEFAULT_CATEGORY = "Прочее"
PREFIX_CATEGORY = {
    "ENG": "Двигатели",
    "GBX": "Коробки передач",
    "TRB": "Наддув",
    "SC": "Наддув",
    "DSK": "Тормозные диски",
    "CLP": "Тормозные суппорты",
    "ABS": "Датчики ABS",
    "OILKIT": "Комплекты ТО",
    "OIL": "Масла и жидкости",
    "GOIL": "Масла и жидкости",
    "COOL": "Масла и жидкости",
    "AFLT": "Фильтры",
    "CAB": "Фильтры",
    "FFLT": "Фильтры",
    "INJ": "Топливная система",
    "FPMP": "Топливная система",
    "HPFP": "Топливная система",
    "PLUG": "Система зажигания",
    "COIL": "Система зажигания",
    "EXH": "Выхлопная система",
}
CATEGORIES = sorted(set(PREFIX_CATEGORY.values()) | {DEFAULT_CATEGORY})
EXPECTED_COLUMNS = ["article", "name", "price", "stock"]

CREATE_NEW = f"""
CREATE TABLE Part_new (
    article TEXT NOT NULL,
    name TEXT NOT NULL,
    price REAL NOT NULL CHECK (price >= 0),
    stock INTEGER NOT NULL DEFAULT 0 CHECK (stock >= 0),
    category TEXT NOT NULL DEFAULT '{DEFAULT_CATEGORY}'
        CHECK (category IN ({", ".join(f"'{c}'" for c in CATEGORIES)})),
    CONSTRAINT Part_PK PRIMARY KEY (article)
)
"""

# префикс артикула - всё до первого дефиса (или весь артикул, если дефиса нет)
COPY_DATA = f"""
INSERT INTO Part_new (article, name, price, stock, category)
SELECT p.article, p.name, p.price, p.stock, COALESCE(m.category, '{DEFAULT_CATEGORY}')
FROM Part p
LEFT JOIN prefix_category m
       ON m.prefix = CASE WHEN instr(p.article, '-') > 0
                          THEN substr(p.article, 1, instr(p.article, '-') - 1)
                          ELSE p.article END
"""


def part_columns(conn):
    return [r[1] for r in conn.execute("PRAGMA table_info(Part)")]


def run_migration(conn):
    """Перестраивает Part в одной транзакции. При любой ошибке откатывает и пробрасывает её."""
    conn.execute("PRAGMA foreign_keys = OFF")   # вне транзакции: внутри неё PRAGMA не действует
    try:
        conn.execute("BEGIN")
        conn.execute(CREATE_NEW)
        conn.execute("CREATE TEMP TABLE prefix_category (prefix TEXT PRIMARY KEY, category TEXT NOT NULL)")
        conn.executemany("INSERT INTO prefix_category VALUES (?, ?)", PREFIX_CATEGORY.items())
        conn.execute(COPY_DATA)
        conn.execute("DROP TABLE temp.prefix_category")
        conn.execute("DROP TABLE Part")
        conn.execute("ALTER TABLE Part_new RENAME TO Part")
        violations = conn.execute("PRAGMA foreign_key_check").fetchall()
        if violations:
            raise sqlite3.IntegrityError(f"после миграции нарушены внешние ключи: {violations[:5]}")
        conn.execute("COMMIT")
    except Exception:
        if conn.in_transaction:
            conn.execute("ROLLBACK")
        raise
    finally:
        conn.execute("PRAGMA foreign_keys = ON")


def main():
    parser = argparse.ArgumentParser(description="Миграция: добавить Part.category")
    parser.add_argument("--db", default=str(DEFAULT_DB), help="путь к файлу базы")
    parser.add_argument("--backups", default=str(DEFAULT_BACKUPS), help="папка для резервных копий")
    parser.add_argument("--no-backup", action="store_true", help="не делать резервную копию")
    args = parser.parse_args()
    db_path, backups_dir = Path(args.db), Path(args.backups)

    if not db_path.exists():
        sys.exit(f"База не найдена: {db_path}")

    conn = sqlite3.connect(db_path, isolation_level=None)   # транзакциями управляем сами
    try:
        columns = part_columns(conn)
        if not columns:
            sys.exit("В базе нет таблицы Part")
        if "category" in columns:
            print("Миграция уже выполнена: в таблице Part есть столбец category.")
            return
        if columns != EXPECTED_COLUMNS:
            sys.exit(f"Неожиданная структура Part: {columns}. Ожидалось: {EXPECTED_COLUMNS}")

        if not args.no_backup:
            backup = make_backup(db_path, backups_dir, prefix=BACKUP_PREFIX)
            print(f"Резервная копия: {backup}")

        before = row_counts(db_path)
        try:
            run_migration(conn)
        except (sqlite3.Error, ValueError) as e:
            print(f"Миграция не выполнена, изменения отменены: {e}", file=sys.stderr)
            sys.exit(1)

        after = row_counts(db_path)
        ok = before == after and conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        print(f"Структура Part теперь: {part_columns(conn)}")
        print(f"Проверка: строк до - {sum(before.values())}, после - {sum(after.values())}, "
              f"целостность - {'в порядке' if ok else 'НАРУШЕНА'}")
        print("\nЗапчасти по категориям:")
        for category, n in conn.execute(
                "SELECT category, COUNT(*) FROM Part GROUP BY category ORDER BY COUNT(*) DESC, category"):
            print(f"  {category:<22} {n:>5}")
        if not ok:
            sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()