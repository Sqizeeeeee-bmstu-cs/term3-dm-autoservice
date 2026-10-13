"""Генерирует справочники автосервиса: модели авто, запчасти и их совместимость.

Один запуск создаёт три набора данных в папке data/:
    model.csv                          (model_id, brand, model_name)
    part.csv                           (article, name, price, stock)
    model_part_compatibility.json      (model_id, article)

Запуск из любого места:
    python import/create_catalog.py
    python import/create_catalog.py --format json --compat-format csv

Загружать в таком порядке (из-за внешних ключей): model, part, model_part_compatibility.
"""
import argparse
import csv
import json
import random
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
SEED = 42

# ---------------------------------------------------------------- цены (руб.)
# (минимум, максимум) за ОДНУ штуку до применения коэффициентов бренда и класса
PRICE = {
    "engine_per_cyl": (55_000, 75_000),   # двигатель в сборе, за цилиндр
    "oilkit": (9_000, 18_000),            # комплект ТО: масло + 3 фильтра
    "injector_port": (3_500, 6_500),      # форсунка, распределённый впрыск
    "injector_di": (12_000, 22_000),      # форсунка, непосредственный впрыск
    "injector_diesel": (20_000, 35_000),  # форсунка дизеля
    "fuel_pump": (8_000, 22_000),
    "fuel_filter": (1_200, 4_500),
    "air_filter": (1_500, 4_500),
    "turbo": (90_000, 160_000),           # одна турбина
    "supercharger": (200_000, 320_000),
    "plug": (1_200, 3_200),               # одна свеча
    "coil": (3_500, 8_000),               # одна катушка
    "hpfp": (35_000, 90_000),             # ТНВД
    "gearbox": (180_000, 420_000),
    "cabin_filter": (1_200, 3_800),
    "caliper": (15_000, 38_000),          # один суппорт
    "abs": (2_500, 6_500),                # один датчик
    "disc": (9_000, 22_000),              # один штатный диск
    "disc_ceramic": (180_000, 330_000),   # один карбон-керамический диск
    "downpipe": (35_000, 80_000),
    "catback": (55_000, 130_000),
    "full_exhaust": (110_000, 260_000),
    "oil_1l": (1_200, 2_500),
    "oil_5l": (4_500, 9_500),
    "gear_oil_5l": (6_000, 18_000),
    "coolant_1_5l": (1_000, 2_200),
    "coolant_5l": (2_800, 6_500),
}

BRAND_FACTOR = {"BMW": 1.3, "Mercedes-Benz": 1.5, "Audi": 1.2, "Porsche": 2.5}
ASP_FACTOR = {"NA": 1.0, "T": 1.4, "TT": 1.8, "SC": 1.5}

# ---------------------------------------------------------------- двигатели
# ключ: (название, цилиндров, наддув NA/T/TT/SC, топливо, непосредств. впрыск, коэфф. класса)
ENGINES = {
    # BMW
    "M50B25": ("M50B25 2.5 (I6)", 6, "NA", "petrol", False, 1.0),
    "M60B40": ("M60B40 4.0 (V8)", 8, "NA", "petrol", False, 1.0),
    "M54B30": ("M54B30 3.0 (I6)", 6, "NA", "petrol", False, 1.0),
    "N46B20": ("N46B20 2.0 (I4)", 4, "NA", "petrol", False, 1.0),
    "N52B30": ("N52B30 3.0 (I6)", 6, "NA", "petrol", False, 1.0),
    "N54B30": ("N54B30 3.0 (I6 Twin Turbo)", 6, "TT", "petrol", True, 1.1),
    "N55B30": ("N55B30 3.0 (I6 Turbo)", 6, "T", "petrol", True, 1.0),
    "N63B44": ("N63B44 4.4 (V8 Twin Turbo)", 8, "TT", "petrol", True, 1.1),
    "S63B44": ("S63B44 4.4 (V8 Twin Turbo)", 8, "TT", "petrol", True, 1.8),
    "B48B20": ("B48B20 2.0 (I4 Turbo)", 4, "T", "petrol", True, 1.0),
    "B58B30": ("B58B30 3.0 (I6 Turbo)", 6, "T", "petrol", True, 1.0),
    "S68B44": ("S68B44 4.4 (V8 Twin Turbo, гибрид)", 8, "TT", "petrol", True, 1.9),
    "S58B30": ("S58B30 3.0 (I6 Twin Turbo)", 6, "TT", "petrol", True, 1.8),
    "S55B30": ("S55B30 3.0 (I6 Twin Turbo)", 6, "TT", "petrol", True, 1.7),
    # Mercedes-Benz
    "M276_35": ("M276 3.5 (V6)", 6, "NA", "petrol", True, 1.0),
    "M157": ("M157 5.5 (V8 Biturbo)", 8, "TT", "petrol", True, 1.8),
    "M264": ("M264 2.0 (I4 Turbo)", 4, "T", "petrol", True, 1.0),
    "M256": ("M256 3.0 (I6 Turbo)", 6, "T", "petrol", True, 1.2),
    "M273": ("M273 5.5 (V8)", 8, "NA", "petrol", True, 1.0),
    "M275": ("M275 5.5 (V12 Biturbo)", 12, "TT", "petrol", True, 1.4),
    "M276_30": ("M276 3.0 (V6 Biturbo)", 6, "TT", "petrol", True, 1.0),
    "M279": ("M279 6.0 (V12 Biturbo)", 12, "TT", "petrol", True, 1.5),
    "M177": ("M177 4.0 (V8 Biturbo)", 8, "TT", "petrol", True, 1.6),
    "M274": ("M274 2.0 (I4 Turbo)", 4, "T", "petrol", True, 1.0),
    "M254": ("M254 2.0 (I4 Turbo, мягкий гибрид)", 4, "T", "petrol", True, 1.1),
    "M139": ("M139 2.0 (I4 Turbo)", 4, "T", "petrol", True, 1.8),
    # Audi
    "EA837_30": ("3.0 TFSI EA837 (V6, нагнетатель)", 6, "SC", "petrol", True, 1.0),
    "TDI_C7": ("3.0 TDI EA897 (V6 Turbo)", 6, "T", "diesel", True, 1.0),
    "EA839_30": ("3.0 TFSI EA839 (V6 Turbo)", 6, "T", "petrol", True, 1.1),
    "TDI_EVO": ("3.0 TDI EA897 evo (V6 Turbo)", 6, "T", "diesel", True, 1.1),
    "ALT_20": ("2.0 ALT (I4)", 4, "NA", "petrol", False, 1.0),
    "BEX_30": ("3.0 V6 BEX", 6, "NA", "petrol", False, 1.0),
    "BGB_20": ("2.0 TFSI BGB (I4 Turbo)", 4, "T", "petrol", True, 1.0),
    "BKH_32": ("3.2 FSI BKH (V6)", 6, "NA", "petrol", True, 1.0),
    "EA888_G2": ("2.0 TFSI EA888 gen2 (I4 Turbo)", 4, "T", "petrol", True, 1.0),
    "EA888_G3": ("2.0 TFSI EA888 gen3 (I4 Turbo)", 4, "T", "petrol", True, 1.0),
    # Porsche
    "9A1_34": ("9A1 3.4 (flat-6)", 6, "NA", "petrol", True, 1.3),
    "9A1_38": ("9A1 3.8 (flat-6)", 6, "NA", "petrol", True, 1.5),
    "9A2_30": ("9A2 3.0 (flat-6 Twin Turbo)", 6, "TT", "petrol", True, 1.4),
    "9A1_38T": ("9A1 3.8 (flat-6 Twin Turbo)", 6, "TT", "petrol", True, 2.0),
    "9A1_40": ("4.0 (flat-6, GT3 RS 991)", 6, "NA", "petrol", True, 2.2),
    "9A2EVO_30": ("9A2 EVO 3.0 (flat-6 Twin Turbo)", 6, "TT", "petrol", True, 1.5),
    "9A2_37T": ("3.7 (flat-6 Twin Turbo, Turbo S 992)", 6, "TT", "petrol", True, 2.0),
    "M97_40": ("4.0 (flat-6, GT3 RS 992)", 6, "NA", "petrol", True, 2.2),
}

# ---------------------------------------------------------------- модели
# код, бренд, название, двигатели, коробка, семейство коробки (для масла),
# карбон-керамика, коэффициент класса (тормоза, выхлоп)
MODELS = [
    # BMW
    ("E34", "BMW", "5 Series E34", ["M50B25", "M60B40"], "ZF 5HP", "ZF5HP", False, 1.0),
    ("E46", "BMW", "3 Series E46", ["M54B30", "N46B20"], "ZF 5HP", "ZF5HP", False, 1.0),
    ("E60", "BMW", "5 Series E60", ["N52B30", "N54B30"], "ZF 6HP", "ZF6HP", False, 1.0),
    ("F10", "BMW", "5 Series F10", ["N55B30", "N63B44"], "ZF 8HP", "ZF8HP", False, 1.0),
    ("F90", "BMW", "M5 F90", ["S63B44"], "ZF 8HP (M Steptronic)", "ZF8HP", True, 1.7),
    ("G30", "BMW", "5 Series G30", ["B48B20", "B58B30"], "ZF 8HP", "ZF8HP", False, 1.0),
    ("G90", "BMW", "M5 G90", ["S68B44"], "ZF 8HP (M Steptronic)", "ZF8HP", True, 1.8),
    ("G42", "BMW", "2 Series G42", ["B48B20", "B58B30"], "ZF 8HP", "ZF8HP", False, 1.0),
    ("E90", "BMW", "3 Series E90", ["N52B30", "N54B30"], "ZF 6HP", "ZF6HP", False, 1.0),
    ("G20", "BMW", "3 Series G20", ["B48B20", "B58B30"], "ZF 8HP", "ZF8HP", False, 1.0),
    ("G80", "BMW", "M3 G80", ["S58B30"], "ZF 8HP (M Steptronic)", "ZF8HP", True, 1.7),
    ("G82", "BMW", "M4 G82", ["S58B30"], "ZF 8HP (M Steptronic)", "ZF8HP", True, 1.7),
    ("F82", "BMW", "M4 F82", ["S55B30"], "Getrag 7DCI600 (M DCT)", "BMWDCT", True, 1.6),
    # Mercedes-Benz
    ("W212", "Mercedes-Benz", "E-Class W212", ["M276_35", "M157"], "7G-Tronic Plus", "MB7G", False, 1.0),
    ("W213", "Mercedes-Benz", "E-Class W213", ["M264", "M256"], "9G-Tronic", "MB9G", False, 1.0),
    ("W221", "Mercedes-Benz", "S-Class W221", ["M273", "M275"], "7G-Tronic", "MB7G", False, 1.1),
    ("W222", "Mercedes-Benz", "S-Class W222", ["M276_30", "M279"], "9G-Tronic", "MB9G", False, 1.2),
    ("W223", "Mercedes-Benz", "S-Class W223", ["M256", "M177"], "9G-Tronic", "MB9G", False, 1.3),
    ("C292", "Mercedes-Benz", "GLE Coupe C292", ["M276_30", "M157"], "9G-Tronic", "MB9G", True, 1.3),
    ("W205", "Mercedes-Benz", "C-Class W205", ["M274", "M177"], "9G-Tronic", "MB9G", True, 1.2),
    ("W206", "Mercedes-Benz", "C-Class W206", ["M254", "M139"], "9G-Tronic", "MB9G", True, 1.2),
    # Audi
    ("A6C7", "Audi", "A6 C7", ["EA837_30", "TDI_C7"], "Tiptronic 8 (ZF 8HP)", "ZF8HP", False, 1.0),
    ("A6C8", "Audi", "A6 C8", ["EA839_30", "TDI_EVO"], "S tronic 7", "AUDI_S7", False, 1.0),
    ("A4B6", "Audi", "A4 B6", ["ALT_20", "BEX_30"], "Multitronic 01J", "AUDI_MT", False, 1.0),
    ("A4B7", "Audi", "A4 B7", ["BGB_20", "BKH_32"], "Tiptronic 6 (ZF 6HP)", "ZF6HP", False, 1.0),
    ("A4B8", "Audi", "A4 B8", ["EA888_G2", "EA837_30"], "S tronic 7", "AUDI_S7", False, 1.0),
    ("A4B9", "Audi", "A4 B9", ["EA888_G3", "TDI_EVO"], "S tronic 7", "AUDI_S7", False, 1.0),
    # Porsche
    ("991CARR", "Porsche", "911 (991) Carrera", ["9A1_34", "9A2_30"], "PDK 7", "PDK", True, 1.2),
    ("991GTS", "Porsche", "911 (991) Carrera GTS", ["9A1_38", "9A2_30"], "PDK 7", "PDK", True, 1.4),
    ("991TARGA", "Porsche", "911 (991) Targa", ["9A1_34", "9A2_30"], "PDK 7", "PDK", True, 1.3),
    ("991TARGAS", "Porsche", "911 (991) Targa S", ["9A1_38", "9A2_30"], "PDK 7", "PDK", True, 1.4),
    ("991TURBOS", "Porsche", "911 (991) Turbo S", ["9A1_38T"], "PDK 7", "PDK", True, 1.8),
    ("991GT3RS", "Porsche", "911 (991) GT3 RS", ["9A1_40"], "PDK 7", "PDK", True, 2.0),
    ("991GT2RS", "Porsche", "911 (991) GT2 RS", ["9A1_38T"], "PDK 7", "PDK", True, 2.2),
    ("992CARR", "Porsche", "911 (992) Carrera", ["9A2EVO_30"], "PDK 8", "PDK", True, 1.3),
    ("992TARGA", "Porsche", "911 (992) Targa", ["9A2EVO_30"], "PDK 8", "PDK", True, 1.4),
    ("992TURBOS", "Porsche", "911 (992) Turbo S", ["9A2_37T"], "PDK 8", "PDK", True, 1.9),
    ("992GT3RS", "Porsche", "911 (992) GT3 RS", ["M97_40"], "PDK 7", "PDK", True, 2.1),
]

# ---------------------------------------------------------------- универсальные позиции
ENGINE_OIL_SPECS = {
    "BMW": [("5W-30", "BMW Longlife-04"), ("5W-40", "BMW Longlife-01")],
    "Mercedes-Benz": [("5W-30", "MB 229.51"), ("5W-40", "MB 229.5")],
    "Audi": [("5W-30", "VW 504.00/507.00"), ("5W-40", "VW 502.00/505.00")],
    "Porsche": [("0W-40", "Porsche A40"), ("5W-40", "Porsche C40")],
}
OIL_BRAND_MULT = {"BMW": 1.1, "Mercedes-Benz": 1.1, "Audi": 1.0, "Porsche": 1.4}

GEAR_OIL_FAMILIES = {
    "ZF5HP": "ZF 5HP", "ZF6HP": "ZF 6HP", "ZF8HP": "ZF 8HP",
    "BMWDCT": "BMW M DCT", "MB7G": "Mercedes 7G-Tronic", "MB9G": "Mercedes 9G-Tronic",
    "AUDI_S7": "Audi S tronic 7", "AUDI_MT": "Audi Multitronic", "PDK": "Porsche PDK",
}


# ---------------------------------------------------------------- генерация
class Catalog:
    def __init__(self, seed):
        self.rng = random.Random(seed)
        self.models = []      # (model_id, brand, name)
        self.parts = []       # dict(article, name, price, stock)
        self.compat = set()   # (model_id, article)
        self._articles = set()

    def price(self, key, factor=1.0, count=1):
        lo, hi = PRICE[key]
        v = self.rng.uniform(lo, hi) * factor * count
        step = 10 if v < 20_000 else 100 if v < 200_000 else 1_000
        return int(round(v / step) * step)

    def stock(self, hi):
        return 0 if self.rng.random() < 0.12 else self.rng.randint(1, hi)

    def add(self, article, name, price, stock, model_ids):
        assert article not in self._articles, f"дубликат артикула {article}"
        assert model_ids, f"у {article} нет совместимых моделей"
        self._articles.add(article)
        self.parts.append({"article": article, "name": name, "price": price, "stock": stock})
        for mid in model_ids:
            self.compat.add((mid, article))


def build(seed=SEED):
    c = Catalog(seed)

    # --- модели
    model_ids = {}
    for i, (code, brand, name, *_rest) in enumerate(MODELS, start=1):
        model_ids[code] = i
        c.models.append((i, brand, name))
    full = {code: f"{brand} {name}" for code, brand, name, *_ in MODELS}

    # --- какие модели используют каждый двигатель
    engine_models = {}
    for code, brand, _name, engines, *_rest in MODELS:
        for e in engines:
            assert e in ENGINES, f"неизвестный двигатель {e}"
            engine_models.setdefault(e, []).append(code)
    engine_brand = {
        e: next(b for code, b, *_ in MODELS if code == codes[0])
        for e, codes in engine_models.items()
    }

    # --- запчасти, привязанные к двигателю
    for e, (ename, cyl, asp, fuel, di, perf) in ENGINES.items():
        mids = [model_ids[m] for m in engine_models[e]]
        bf = BRAND_FACTOR[engine_brand[e]]
        petrol = fuel == "petrol"

        c.add(f"ENG-{e}", f"Двигатель {ename} в сборе",
              c.price("engine_per_cyl", bf * perf * ASP_FACTOR[asp], cyl), c.stock(3), mids)
        c.add(f"OILKIT-{e}", f"Комплект ТО {ename}: масло и фильтры",
              c.price("oilkit", bf), c.stock(30), mids)
        inj_key = "injector_diesel" if not petrol else ("injector_di" if di else "injector_port")
        c.add(f"INJ-{e}", f"Форсунки {ename}, комплект {cyl} шт.",
              c.price(inj_key, bf, cyl), c.stock(10), mids)
        c.add(f"FPMP-{e}", f"Топливный насос {ename}",
              c.price("fuel_pump", bf), c.stock(10), mids)
        c.add(f"FFLT-{e}", f"Топливный фильтр {ename}",
              c.price("fuel_filter", bf), c.stock(30), mids)
        c.add(f"AFLT-{e}", f"Воздушный фильтр {ename}",
              c.price("air_filter", bf), c.stock(30), mids)
        if asp in ("T", "TT"):
            n = 2 if asp == "TT" else 1
            label = "Комплект турбин (2 шт.)" if n == 2 else "Турбина"
            c.add(f"TRB-{e}", f"{label} {ename}",
                  c.price("turbo", bf * perf, n), c.stock(3), mids)
        if asp == "SC":
            c.add(f"SC-{e}", f"Нагнетатель (компрессор) {ename}",
                  c.price("supercharger", bf), c.stock(3), mids)
        if petrol:
            c.add(f"PLUG-{e}", f"Свечи зажигания {ename}, комплект {cyl} шт.",
                  c.price("plug", bf, cyl), c.stock(30), mids)
            c.add(f"COIL-{e}", f"Катушки зажигания {ename}, комплект {cyl} шт.",
                  c.price("coil", bf, cyl), c.stock(15), mids)
        if di:
            c.add(f"HPFP-{e}", f"ТНВД {ename}",
                  c.price("hpfp", bf), c.stock(8), mids)

    # --- запчасти, привязанные к модели
    for code, brand, name, engines, gearbox, gfam, ceramic, perf in MODELS:
        mid = [model_ids[code]]
        label = full[code]
        bf = BRAND_FACTOR[brand]
        turbo = any(ENGINES[e][2] in ("T", "TT", "SC") for e in engines)

        c.add(f"GBX-{code}", f"Коробка передач {gearbox}, {label}",
              c.price("gearbox", bf * perf), c.stock(3), mid)
        c.add(f"CAB-{code}", f"Салонный фильтр, {label}",
              c.price("cabin_filter", bf), c.stock(30), mid)

        for pos, pos_name in (("FL", "передний левый"), ("FR", "передний правый"),
                              ("RL", "задний левый"), ("RR", "задний правый")):
            c.add(f"CLP-{pos}-{code}", f"Суппорт тормозной {pos_name}, {label}",
                  c.price("caliper", bf * perf), c.stock(8), mid)
            c.add(f"ABS-{pos}-{code}", f"Датчик ABS {pos_name}, {label}",
                  c.price("abs", bf), c.stock(25), mid)

        for axle, axle_name in (("F", "передний"), ("R", "задний")):
            c.add(f"DSK-{axle}-{code}", f"Диск тормозной {axle_name}, {label}",
                  c.price("disc", bf * perf), c.stock(15), mid)
            if ceramic:
                c.add(f"DSK-{axle}-CC-{code}", f"Диск тормозной {axle_name} карбон-керамика, {label}",
                      c.price("disc_ceramic", bf), c.stock(2), mid)

        if turbo:
            c.add(f"EXH-DP-{code}", f"Даунпайп спортивный, {label}",
                  c.price("downpipe", bf * perf), c.stock(6), mid)
        c.add(f"EXH-CB-{code}", f"Выхлопная система cat-back спортивная, {label}",
              c.price("catback", bf * perf), c.stock(6), mid)
        c.add(f"EXH-FS-{code}", f"Выхлопная система полная (прямоток), {label}",
              c.price("full_exhaust", bf * perf), c.stock(4), mid)

    # --- универсальные: моторные масла (по бренду)
    for brand, specs in ENGINE_OIL_SPECS.items():
        mids = [model_ids[code] for code, b, *_ in MODELS if b == brand]
        mult = OIL_BRAND_MULT[brand]
        for visc, approval in specs:
            tag = visc.replace("-", "")
            for vol, key in (("1", "oil_1l"), ("5", "oil_5l")):
                c.add(f"OIL-{brand.split('-')[0].upper()}-{tag}-{vol}L",
                      f"Масло моторное {visc} ({approval}), {vol} л",
                      c.price(key, mult), c.stock(60), mids)

    # --- универсальные: масла для коробок (по семейству коробки)
    for fam, fam_name in GEAR_OIL_FAMILIES.items():
        mids = [model_ids[code] for code, *_r, gf, _c, _p in MODELS if gf == fam]
        if not mids:
            continue
        c.add(f"GOIL-{fam}", f"Масло для коробки {fam_name}, 5 л",
              c.price("gear_oil_5l"), c.stock(30), mids)

    # --- универсальные: антифриз (по бренду)
    for brand in ENGINE_OIL_SPECS:
        mids = [model_ids[code] for code, b, *_ in MODELS if b == brand]
        tag = brand.split("-")[0].upper()
        for vol, key in (("1.5", "coolant_1_5l"), ("5", "coolant_5l")):
            c.add(f"COOL-{tag}-{vol.replace('.', '_')}L",
                  f"Антифриз для {brand}, {vol} л", c.price(key), c.stock(60), mids)

    return c


# ---------------------------------------------------------------- запись файлов
def write_rows(path: Path, fields, rows, fmt):
    if fmt == "csv":
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(rows)
    else:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False, indent=2)


def main():
    parser = argparse.ArgumentParser(description="Создать файлы данных: модели, запчасти, совместимость")
    parser.add_argument("--format", choices=["csv", "json"], default="csv",
                        help="формат для model и part (по умолчанию csv)")
    parser.add_argument("--compat-format", choices=["csv", "json"], default="json",
                        help="формат для совместимости (по умолчанию json)")
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args()

    c = build(args.seed)
    DATA_DIR.mkdir(exist_ok=True)

    models = [{"model_id": i, "brand": b, "model_name": n} for i, b, n in c.models]
    compat = [{"model_id": m, "article": a} for m, a in sorted(c.compat)]

    outputs = [
        (f"model.{args.format}", ["model_id", "brand", "model_name"], models, args.format),
        (f"part.{args.format}", ["article", "name", "price", "stock"], c.parts, args.format),
        (f"model_part_compatibility.{args.compat_format}", ["model_id", "article"], compat, args.compat_format),
    ]
    for filename, fields, rows, fmt in outputs:
        write_rows(DATA_DIR / filename, fields, rows, fmt)
        print(f"{filename}: {len(rows)} строк")

    groups = Counter(p["article"].split("-")[0] for p in c.parts)
    print("\nЗапчасти по группам:", ", ".join(f"{k}={v}" for k, v in sorted(groups.items())))


if __name__ == "__main__":
    main()
