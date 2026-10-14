"""Загружает данные из CSV или JSON в таблицу SQLite (через SQLAlchemy).

Примеры (из любого места):
    python import/import.py --file data/model.csv
    python import/import.py --file data/client.json
    python import/import.py --file data/part.csv --table Part
    python import/import.py --file data/model.csv --db db/autoservice.sqlite
"""
import argparse
import csv
import json
import sys
from pathlib import Path

from sqlalchemy import Float, Integer, MetaData, Table, create_engine, event, inspect
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB = ROOT / "db" / "autoservice.sqlite"


@event.listens_for(Engine, "connect")
def _enable_foreign_keys(dbapi_connection, _record):
    # PRAGMA действует только на текущее соединение, поэтому включаем на каждом
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")
    cursor.close()


def resolve_path(p: str) -> Path:
    path = Path(p)
    return path if path.is_absolute() else Path.cwd() / path


def read_csv(path: Path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    # пустое поле в CSV = NULL, а не пустая строка
    return [{k: (v if v != "" else None) for k, v in row.items()} for row in rows]


def read_json(path: Path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list) or not all(isinstance(r, dict) for r in data):
        raise ValueError("JSON должен быть массивом объектов [{...}, {...}]")
    return data


def find_table_name(engine, name: str) -> str:
    tables = inspect(engine).get_table_names()
    for t in tables:
        if t.lower() == name.lower():
            return t
    raise ValueError(f"таблица '{name}' не найдена. Есть: {', '.join(tables)}")


def coerce(table: Table, row: dict, line: int) -> dict:
    """Приводит значения из файла к типам столбцов (CSV отдаёт всё строками)."""
    out = {}
    for col_name, value in row.items():
        col_type = table.c[col_name].type
        if value is not None and isinstance(col_type, (Integer, Float)):
            py_type = int if isinstance(col_type, Integer) else float
            try:
                value = py_type(value)
            except (TypeError, ValueError):
                raise ValueError(
                    f"строка {line}: значение {value!r} в столбце {col_name} "
                    f"не подходит под тип {py_type.__name__}"
                )
        out[col_name] = value
    return out


def main():
    parser = argparse.ArgumentParser(description="Импорт CSV/JSON в SQLite")
    parser.add_argument("--file", required=True, help="путь к .csv или .json")
    parser.add_argument("--table", help="имя таблицы (по умолчанию из имени файла)")
    parser.add_argument("--db", default=str(DEFAULT_DB), help="путь к файлу БД")
    args = parser.parse_args()

    file_path = resolve_path(args.file)
    db_path = resolve_path(args.db)

    if not file_path.exists():
        sys.exit(f"Ошибка: файл не найден: {file_path}")
    if not db_path.exists():
        sys.exit(f"Ошибка: база не найдена: {db_path}")

    ext = file_path.suffix.lower()
    try:
        if ext == ".csv":
            rows = read_csv(file_path)
        elif ext == ".json":
            rows = read_json(file_path)
        else:
            sys.exit(f"Ошибка: неподдерживаемый формат '{ext}' (нужен .csv или .json)")
    except (ValueError, json.JSONDecodeError, UnicodeDecodeError) as e:
        sys.exit(f"Ошибка чтения файла: {e}")

    if not rows:
        sys.exit("Файл не содержит данных")

    engine = create_engine(f"sqlite:///{db_path}")
    try:
        table_name = find_table_name(engine, args.table or file_path.stem)
        table = Table(table_name, MetaData(), autoload_with=engine)

        file_cols = list(rows[0].keys())
        unknown = [c for c in file_cols if c not in table.c]
        if unknown:
            raise ValueError(
                f"в файле есть столбцы, которых нет в таблице {table_name}: {unknown}. "
                f"Столбцы таблицы: {list(table.c.keys())}"
            )

        # engine.begin(): одна транзакция, commit при успехе, rollback при исключении
        with engine.begin() as conn:
            for i, row in enumerate(rows, start=1):
                values = coerce(table, {c: row.get(c) for c in file_cols}, i)
                try:
                    conn.execute(table.insert().values(**values))
                except IntegrityError as e:
                    raise ValueError(f"строка {i}: {e.orig} | {row}") from e

        print(f"Загружено {len(rows)} строк в таблицу {table_name} из {file_path.name}")
    except (ValueError, SQLAlchemyError) as e:
        print(f"Ошибка, загрузка отменена (откат): {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
