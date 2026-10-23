"""Экспортирует данные из таблицы SQLite в файл CSV или JSON (через SQLAlchemy).

Примеры использования:
    python export/export.py --table Part --file part.csv
    python export/export.py --table Client --file clients --format json
    python export/export.py --table Model --file backups/model.csv
"""
import argparse
import csv
import json
import sys
from pathlib import Path

from sqlalchemy import MetaData, Table, create_engine, inspect
from sqlalchemy.exc import SQLAlchemyError

# Корневые папки
SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent
DEFAULT_DB = ROOT / "db" / "autoservice.sqlite"

# Дефолтная папка экспорта (../data_export/ относительно скрипта)
DEFAULT_EXPORT_DIR = SCRIPT_DIR.parent / "data_export"


def resolve_export_path(p: str) -> Path:
    path = Path(p)
    if path.parent == Path("."):
        return DEFAULT_EXPORT_DIR / path
    
    return path if path.is_absolute() else Path.cwd() / path


def resolve_path(p: str) -> Path:
    path = Path(p)
    return path if path.is_absolute() else Path.cwd() / path


def find_table_name(engine, name: str) -> str:
    tables = inspect(engine).get_table_names()
    for t in tables:
        if t.lower() == name.lower():
            return t
    raise ValueError(f"таблица '{name}' не найдена. Есть: {', '.join(tables)}")


def save_csv(path: Path, columns: list, rows: list):
    with open(path, mode="w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: (v if v is not None else "") for k, v in row.items()})


def save_json(path: Path, rows: list):
    with open(path, mode="w", encoding="utf-8") as f:
        # ensure_ascii=False сохраняет кириллицу как текст, а не \u0430
        json.dump(rows, f, ensure_ascii=False, indent=4)


def main():
    parser = argparse.ArgumentParser(description="Экспорт таблицы SQLite в CSV/JSON")
    parser.add_argument("--table", required=True, help="имя таблицы для экспорта")
    parser.add_argument("--file", required=True, help="имя файла или путь для сохранения")
    parser.add_argument("--format", choices=["csv", "json"], help="формат (если не указан, берется из расширения файла)")
    parser.add_argument("--db", default=str(DEFAULT_DB), help="путь к файлу БД")
    args = parser.parse_args()

    db_path = resolve_path(args.db)
    file_path = resolve_export_path(args.file)

    if not db_path.exists():
        sys.exit(f"Ошибка: база данных не найдена: {db_path}")

    # Определяем формат: либо явный флаг --format, либо расширение файла
    fmt = args.format or file_path.suffix.lower().lstrip(".")
    if fmt not in ["csv", "json"]:
        sys.exit(f"Ошибка: неопределенный формат '{fmt}'. Укажите расширение у файла (.csv/.json) или флаг --format")

    # Если у файла не было расширения, добавляем его автоматически
    if not file_path.suffix:
        file_path = file_path.with_suffix(f".{fmt}")

    engine = create_engine(f"sqlite:///{db_path}")
    try:
        table_name = find_table_name(engine, args.table)
        table = Table(table_name, MetaData(), autoload_with=engine)
        columns = list(table.c.keys())

        with engine.connect() as conn:
            result = conn.execute(table.select())
            rows = [dict(row) for row in result.mappings()]

        if not rows:
            print(f"Предупреждение: таблица '{table_name}' пуста. Будет создан пустой файл.")

        # Автоматически создаст папку ../data_export/, если ее не было
        file_path.parent.mkdir(parents=True, exist_ok=True)

        if fmt == "csv":
            save_csv(file_path, columns, rows)
        elif fmt == "json":
            save_json(file_path, rows)

        print(f"Успешно экспортировано {len(rows)} строк из таблицы '{table_name}' -> {file_path}")

    except (ValueError, SQLAlchemyError) as e:
        print(f"Ошибка экспорта: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
