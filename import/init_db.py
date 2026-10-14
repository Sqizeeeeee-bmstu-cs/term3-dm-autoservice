"""Создаёт структуру БД из SQL-скрипта или печатает число строк в таблицах.

    python import/init_db.py            # пересоздать структуру (скрипт начинается с DROP TABLE IF EXISTS)
    python import/init_db.py --stats    # сколько строк в каждой таблице
    python import/init_db.py --db db/autoservice.sqlite --schema lab1/create_tables.sql
"""
import argparse
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def resolve(p):
    path = Path(p)
    return path if path.is_absolute() else Path.cwd() / path


def main():
    parser = argparse.ArgumentParser(description="Создать структуру БД или показать статистику")
    parser.add_argument("--db", default=str(ROOT / "db" / "autoservice.sqlite"))
    parser.add_argument("--schema", default=str(ROOT / "lab1" / "create_tables.sql"))
    parser.add_argument("--stats", action="store_true", help="показать число строк в таблицах")
    args = parser.parse_args()

    db_path, schema = resolve(args.db), resolve(args.schema)

    if args.stats:
        if not db_path.exists():
            sys.exit(f"База не найдена: {db_path}")
        conn = sqlite3.connect(db_path)
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
        width = max(len(t) for t in tables)
        total = 0
        for t in tables:
            n = conn.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
            total += n
            print(f"  {t:<{width}}  {n:>7}")
        print(f"  {'ИТОГО':<{width}}  {total:>7}")
        conn.close()
        return

    if not schema.exists():
        sys.exit(f"Не найден SQL-скрипт: {schema}")
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(schema.read_text(encoding="utf-8"))
        conn.commit()
    except sqlite3.Error as e:
        sys.exit(f"Ошибка в SQL-скрипте: {e}")
    n = conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchone()[0]
    conn.close()
    print(f"Структура создана: {n} таблиц -> {db_path}")


if __name__ == "__main__":
    main()
