"""Sample data sets for `python -m lime_warehouse.seed --demo <name>`.

Each set holds at least 50 rows for every table it fills: locations, items, stock (opening balances)
and purchase orders. Add a set by defining a SeedProfile and registering it in PROFILES.

A location's `zone` is its physical address in the building: "<area>, Rack <nn>". Its code is
"<area prefix>-<rack>-<bin>", so a picker can walk to it.
"""

from dataclasses import dataclass

from lime_warehouse.catalog.models import STORAGE


@dataclass(frozen=True)
class SeedProfile:
    description: str
    locations: list[tuple[str, str, str]]  # (code, zone, kind)
    items: list[tuple[str, str, str]]  # (sku, name, unit)
    stock: list[tuple[str, str, int]]  # (sku, location code, quantity) loaded as opening balances
    purchase_orders: list[tuple[str, str, list[tuple[str, int]]]]  # (po number, supplier, [(sku, qty)])


def _locations(areas: list[tuple[str, str, int, int]], rack_word: str = "Rack") -> list[tuple[str, str, str]]:
    """Expand (code prefix, area name, racks, bins per rack) into one storage bin per position."""
    return [
        (f"{prefix}-{rack:02d}-{bin_no:02d}", f"{area}, {rack_word} {rack:02d}", STORAGE)
        for prefix, area, racks, bins in areas
        for rack in range(1, racks + 1)
        for bin_no in range(1, bins + 1)
    ]


def _stock(
    items: list[tuple[str, str, str]], locations: list[tuple[str, str, str]]
) -> list[tuple[str, str, int]]:
    """Every item gets a main bin; the first ten also get a second bin, so some items sit in two places."""
    skus = [sku for sku, _, _ in items]
    codes = [code for code, _, _ in locations]
    rows = [(sku, codes[i % len(codes)], 20 + (i * 37) % 180) for i, sku in enumerate(skus)]
    rows += [(skus[i], codes[(i + len(codes) // 2) % len(codes)], 15 + (i * 13) % 60) for i in range(10)]
    return rows


def _purchase_orders(
    items: list[tuple[str, str, str]], suppliers: list[str], number_prefix: str, count: int = 50
) -> list[tuple[str, str, list[tuple[str, int]]]]:
    """`count` open orders, each with three distinct items, rotating through the suppliers."""
    skus = [sku for sku, _, _ in items]
    orders = []
    for k in range(count):
        lines = [
            (skus[(k * 3 + j * 5 + j * j) % len(skus)], 20 + ((k * 7 + j * 11) % 19) * 5) for j in range(3)
        ]
        orders.append((f"{number_prefix}{k + 1:04d}", suppliers[k % len(suppliers)], lines))
    return orders


_FRUIT_LOCATIONS = _locations(
    [
        ("FA", "Ambient Hall A", 4, 4),
        ("FC", "Cold Room 1", 3, 4),
        ("FR", "Ripening Room", 2, 4),
        ("FF", "Freezer Bay", 2, 3),
        ("FD", "Dispatch Bay North", 2, 4),
    ]
)
_FRUIT_ITEMS = [
    ("MANGO-10", "Mango, 10 kg case", "case"),
    ("LIME-05", "Lime, 5 kg case", "case"),
    ("BANANA-18", "Banana, 18 kg box", "box"),
    ("PINEAPPLE-06", "Pineapple, 6 pc crate", "crate"),
    ("AVOCADO-04", "Avocado Hass, 4 kg tray", "tray"),
    ("PAPAYA-08", "Papaya, 8 kg case", "case"),
    ("APPLE-GALA-18", "Apple Gala, 18 kg box", "box"),
    ("APPLE-FUJI-18", "Apple Fuji, 18 kg box", "box"),
    ("APPLE-GREEN-18", "Apple Granny Smith, 18 kg box", "box"),
    ("PEAR-12", "Pear Conference, 12 kg case", "case"),
    ("ORANGE-15", "Orange Valencia, 15 kg carton", "carton"),
    ("BLOODORANGE-10", "Blood orange, 10 kg case", "case"),
    ("MANDARIN-10", "Mandarin, 10 kg case", "case"),
    ("CLEMENTINE-10", "Clementine, 10 kg case", "case"),
    ("LEMON-10", "Lemon, 10 kg case", "case"),
    ("GRAPEFRUIT-15", "Grapefruit, 15 kg carton", "carton"),
    ("GRAPE-RED-08", "Red grape seedless, 8 kg case", "case"),
    ("GRAPE-GREEN-08", "Green grape seedless, 8 kg case", "case"),
    ("STRAWBERRY-02", "Strawberry, 2 kg tray", "tray"),
    ("BLUEBERRY-01", "Blueberry, 1 kg tray", "tray"),
    ("RASPBERRY-01", "Raspberry, 1 kg tray", "tray"),
    ("BLACKBERRY-01", "Blackberry, 1 kg tray", "tray"),
    ("CRANBERRY-02", "Cranberry, 2 kg bag", "bag"),
    ("CHERRY-05", "Cherry, 5 kg case", "case"),
    ("PEACH-05", "Peach, 5 kg tray", "tray"),
    ("NECTARINE-05", "Nectarine, 5 kg tray", "tray"),
    ("PLUM-05", "Plum, 5 kg tray", "tray"),
    ("APRICOT-05", "Apricot, 5 kg tray", "tray"),
    ("WATERMELON-20", "Watermelon, 20 kg bin", "bin"),
    ("CANTALOUPE-12", "Cantaloupe, 12 kg case", "case"),
    ("HONEYDEW-12", "Honeydew melon, 12 kg case", "case"),
    ("KIWI-03", "Kiwi, 3 kg tray", "tray"),
    ("POMEGRANATE-04", "Pomegranate, 4 kg case", "case"),
    ("FIG-02", "Fig, 2 kg tray", "tray"),
    ("DATE-05", "Medjool date, 5 kg box", "box"),
    ("COCONUT-12", "Coconut, 12 pc sack", "sack"),
    ("GUAVA-05", "Guava, 5 kg case", "case"),
    ("PASSIONFRUIT-02", "Passion fruit, 2 kg tray", "tray"),
    ("LYCHEE-02", "Lychee, 2 kg box", "box"),
    ("DRAGONFRUIT-04", "Dragon fruit, 4 kg case", "case"),
    ("STARFRUIT-03", "Star fruit, 3 kg case", "case"),
    ("PERSIMMON-05", "Persimmon, 5 kg tray", "tray"),
    ("QUINCE-05", "Quince, 5 kg case", "case"),
    ("PLANTAIN-18", "Plantain, 18 kg box", "box"),
    ("JACKFRUIT-10", "Jackfruit, 10 kg crate", "crate"),
    ("RAMBUTAN-02", "Rambutan, 2 kg box", "box"),
    ("MANGOSTEEN-02", "Mangosteen, 2 kg box", "box"),
    ("TAMARIND-05", "Tamarind, 5 kg box", "box"),
    ("SOURSOP-05", "Soursop, 5 kg case", "case"),
    ("CUSTARDAPPLE-05", "Custard apple, 5 kg case", "case"),
    ("LONGAN-02", "Longan, 2 kg box", "box"),
]
_FRUIT_SUPPLIERS = [
    "Tropico Growers Ltd",
    "Sunridge Orchards",
    "Costa Verde Exports",
    "Hillcrest Fruit Co",
    "Pacific Citrus Group",
    "Orchard Lane Farms",
    "Bluewater Berry Co",
    "Golden Valley Produce",
]

_VEG_LOCATIONS = _locations(
    [
        ("VD", "Dry Store", 4, 4),
        ("VC", "Cold Room 2", 3, 4),
        ("VR", "Root Cellar", 2, 4),
        ("VF", "Freezer Bay", 2, 3),
        ("VX", "Dispatch Bay South", 2, 4),
    ]
)
_VEG_ITEMS = [
    ("TOMATO-06", "Tomato, 6 kg crate", "crate"),
    ("POTATO-25", "Potato, 25 kg sack", "sack"),
    ("ONION-20", "Onion, 20 kg sack", "sack"),
    ("CARROT-10", "Carrot, 10 kg bag", "bag"),
    ("LETTUCE-12", "Lettuce, 12 head box", "box"),
    ("PEPPER-05", "Bell pepper, 5 kg case", "case"),
    ("CUCUMBER-10", "Cucumber, 10 kg case", "case"),
    ("ZUCCHINI-10", "Zucchini, 10 kg case", "case"),
    ("EGGPLANT-08", "Eggplant, 8 kg case", "case"),
    ("BROCCOLI-08", "Broccoli, 8 kg carton", "carton"),
    ("CAULIFLOWER-08", "Cauliflower, 8 head carton", "carton"),
    ("CABBAGE-GREEN-15", "Green cabbage, 15 kg bag", "bag"),
    ("CABBAGE-RED-15", "Red cabbage, 15 kg bag", "bag"),
    ("SPINACH-03", "Spinach, 3 kg bag", "bag"),
    ("KALE-03", "Kale, 3 kg box", "box"),
    ("ARUGULA-02", "Arugula, 2 kg box", "box"),
    ("CELERY-12", "Celery, 12 bunch carton", "carton"),
    ("LEEK-10", "Leek, 10 kg case", "case"),
    ("GARLIC-05", "Garlic, 5 kg bag", "bag"),
    ("GINGER-05", "Ginger, 5 kg box", "box"),
    ("SWEETPOTATO-18", "Sweet potato, 18 kg box", "box"),
    ("BEETROOT-10", "Beetroot, 10 kg bag", "bag"),
    ("RADISH-05", "Radish, 5 kg box", "box"),
    ("TURNIP-10", "Turnip, 10 kg bag", "bag"),
    ("PARSNIP-10", "Parsnip, 10 kg bag", "bag"),
    ("PUMPKIN-20", "Pumpkin, 20 kg bin", "bin"),
    ("BUTTERNUT-15", "Butternut squash, 15 kg box", "box"),
    ("CORN-12", "Sweet corn, 12 cob tray", "tray"),
    ("GREENBEAN-05", "Green bean, 5 kg case", "case"),
    ("PEA-05", "Garden pea, 5 kg bag", "bag"),
    ("ASPARAGUS-05", "Asparagus, 5 kg bundle box", "box"),
    ("MUSHROOM-03", "Button mushroom, 3 kg punnet", "punnet"),
    ("SHALLOT-10", "Shallot, 10 kg bag", "bag"),
    ("SPRINGONION-05", "Spring onion, 5 kg box", "box"),
    ("FENNEL-08", "Fennel, 8 kg case", "case"),
    ("ARTICHOKE-08", "Artichoke, 8 kg case", "case"),
    ("BRUSSELS-05", "Brussels sprout, 5 kg bag", "bag"),
    ("OKRA-05", "Okra, 5 kg case", "case"),
    ("CHILI-02", "Red chili, 2 kg box", "box"),
    ("JALAPENO-05", "Jalapeno, 5 kg case", "case"),
    ("BASIL-01", "Basil, 1 kg box", "box"),
    ("PARSLEY-01", "Parsley, 1 kg box", "box"),
    ("CILANTRO-01", "Cilantro, 1 kg box", "box"),
    ("MINT-01", "Mint, 1 kg box", "box"),
    ("DILL-01", "Dill, 1 kg box", "box"),
    ("BOKCHOY-08", "Bok choy, 8 kg carton", "carton"),
    ("CASSAVA-20", "Cassava, 20 kg sack", "sack"),
    ("YAM-18", "Yam, 18 kg box", "box"),
    ("TARO-10", "Taro, 10 kg box", "box"),
    ("KOHLRABI-08", "Kohlrabi, 8 kg case", "case"),
    ("CHARD-03", "Swiss chard, 3 kg box", "box"),
    ("WATERCRESS-01", "Watercress, 1 kg punnet", "punnet"),
]
_VEG_SUPPLIERS = [
    "Greenfield Farms Co",
    "Meadowbrook Growers",
    "Riverbend Produce",
    "Stonegate Market Gardens",
    "Highland Roots Ltd",
    "Evergreen Harvest",
    "Prairie Fresh Co",
    "Valley Salad Growers",
]

_IT_LOCATIONS = _locations(
    [
        ("ITS", "Shelf Hall", 4, 4),
        ("ITC", "Secure Cage", 3, 4),
        ("ITR", "Returns Bench", 2, 4),
        ("ITB", "Cable Room", 2, 3),
        ("ITD", "Dispatch Bay East", 2, 4),
    ]
)
_IT_ITEMS = [
    ("LAPTOP-14", 'Laptop 14", 16 GB / 512 GB', "unit"),
    ("DESKTOP-TW", "Desktop tower, i5 / 16 GB", "unit"),
    ("MONITOR-27", 'Monitor 27" IPS', "unit"),
    ("KEYBOARD-US", "Keyboard, USB, US layout", "unit"),
    ("SSD-1TB", "NVMe SSD, 1 TB", "unit"),
    ("ROUTER-AX", "Wi-Fi 6 router", "unit"),
    ("LAPTOP-15-PRO", 'Laptop 15" Pro, 32 GB / 1 TB', "unit"),
    ("LAPTOP-13-ULTRA", 'Ultrabook 13", 16 GB / 512 GB', "unit"),
    ("WORKSTATION-TW", "Workstation tower, Xeon / 64 GB", "unit"),
    ("MINIPC-NUC", "Mini PC, i5 / 16 GB", "unit"),
    ("AIO-24", 'All-in-one PC 24"', "unit"),
    ("MONITOR-24", 'Monitor 24" IPS', "unit"),
    ("MONITOR-32-4K", 'Monitor 32" 4K', "unit"),
    ("MONITOR-34-UW", 'Monitor 34" ultrawide', "unit"),
    ("KEYBOARD-UK", "Keyboard, USB, UK layout", "unit"),
    ("KEYBOARD-MECH", "Mechanical keyboard, wireless", "unit"),
    ("MOUSE-USB", "Mouse, USB optical", "unit"),
    ("MOUSE-WL", "Mouse, wireless", "unit"),
    ("TRACKPAD-BT", "Trackpad, Bluetooth", "unit"),
    ("WEBCAM-1080", "Webcam 1080p", "unit"),
    ("HEADSET-USB", "Headset, USB", "unit"),
    ("SPEAKER-BT", "Speaker, Bluetooth", "unit"),
    ("MIC-USB", "Microphone, USB", "unit"),
    ("DOCK-USBC", "Docking station, USB-C", "unit"),
    ("DOCK-TB4", "Docking station, Thunderbolt 4", "unit"),
    ("HUB-USB3", "USB 3.0 hub, 4 port", "unit"),
    ("CABLE-HDMI-2", "HDMI cable, 2 m", "box"),
    ("CABLE-DP-2", "DisplayPort cable, 2 m", "box"),
    ("CABLE-USBC-1", "USB-C cable, 1 m", "box"),
    ("CABLE-ETH-5", "Ethernet cable Cat6, 5 m", "box"),
    ("CHARGER-65W", "USB-C charger, 65 W", "unit"),
    ("CHARGER-100W", "USB-C charger, 100 W", "unit"),
    ("POWERBANK-20K", "Power bank, 20,000 mAh", "unit"),
    ("SSD-512GB", "NVMe SSD, 512 GB", "unit"),
    ("SSD-2TB", "NVMe SSD, 2 TB", "unit"),
    ("HDD-4TB", 'Hard drive 3.5", 4 TB', "unit"),
    ("HDD-EXT-2TB", "External hard drive, 2 TB", "unit"),
    ("USB-STICK-64", "USB flash drive, 64 GB", "box"),
    ("USB-STICK-256", "USB flash drive, 256 GB", "box"),
    ("SD-128", "SD card, 128 GB", "box"),
    ("RAM-DDR5-16", "Memory DDR5, 16 GB", "unit"),
    ("RAM-DDR4-8", "Memory DDR4, 8 GB", "unit"),
    ("GPU-RTX-12", "Graphics card, 12 GB", "unit"),
    ("CPU-I5", "Processor, 6-core", "unit"),
    ("CPU-R7", "Processor, 8-core", "unit"),
    ("MOBO-ATX", "Motherboard, ATX", "unit"),
    ("PSU-650W", "Power supply, 650 W", "unit"),
    ("CASE-ATX", "PC case, ATX mid tower", "unit"),
    ("FAN-120", "Case fan, 120 mm", "box"),
    ("SWITCH-24P", "Network switch, 24 port", "unit"),
    ("SWITCH-8P", "Network switch, 8 port", "unit"),
    ("AP-WIFI6", "Wi-Fi 6 access point", "unit"),
    ("FIREWALL-1U", "Firewall appliance, 1U", "unit"),
    ("NAS-4BAY", "NAS, 4 bay", "unit"),
    ("UPS-1500", "UPS, 1500 VA", "unit"),
    ("PRINTER-LASER", "Laser printer, mono", "unit"),
    ("TONER-BLK", "Toner cartridge, black", "box"),
]
_IT_SUPPLIERS = [
    "Nova Computer Supply",
    "Brightbyte Distribution",
    "Silicon Harbor Ltd",
    "Northgate Components",
    "Pixel & Port Wholesale",
    "Datum Trade Co",
    "Circuit City Supply",
    "Ironwire Networks",
]


_APPLIANCE_LOCATIONS = _locations(
    [
        ("EA", "Pasillo Gran Electro", 4, 4),
        ("ET", "Sala de Televisores", 3, 4),
        ("EP", "Zona Pequeño Electro", 2, 4),
        ("EJ", "Jaula de Seguridad", 2, 3),
        ("ED", "Muelle de Despacho", 2, 4),
    ],
    rack_word="Estante",
)
_APPLIANCE_ITEMS = [
    ("TV-LED-32", 'Televisor LED 32" HD', "unidad"),
    ("TV-LED-43", 'Televisor LED 43" Full HD', "unidad"),
    ("TV-4K-50", 'Televisor Smart 4K 50"', "unidad"),
    ("TV-4K-55", 'Televisor Smart 4K 55"', "unidad"),
    ("TV-4K-65", 'Televisor Smart 4K 65"', "unidad"),
    ("TV-OLED-55", 'Televisor OLED 55"', "unidad"),
    ("TV-OLED-65", 'Televisor OLED 65"', "unidad"),
    ("TV-QLED-75", 'Televisor QLED 75"', "unidad"),
    ("BARRA-SONIDO-2", "Barra de sonido 2.1 con subwoofer", "unidad"),
    ("SOPORTE-TV", 'Soporte de pared para TV 32"-65"', "caja"),
    ("LAVADORA-7KG", "Lavadora carga frontal 7 kg", "unidad"),
    ("LAVADORA-9KG", "Lavadora carga frontal 9 kg", "unidad"),
    ("LAVADORA-CS-10KG", "Lavadora carga superior 10 kg", "unidad"),
    ("SECADORA-8KG", "Secadora de condensación 8 kg", "unidad"),
    ("LAVASECA-9KG", "Lavasecadora 9/6 kg", "unidad"),
    ("LAVAVAJILLAS-12", "Lavavajillas 12 cubiertos", "unidad"),
    ("LAVAVAJILLAS-COMP", "Lavavajillas compacto 6 cubiertos", "unidad"),
    ("REFRI-NF-300", "Refrigerador No Frost 300 L", "unidad"),
    ("REFRI-2P-400", "Refrigerador dos puertas 400 L", "unidad"),
    ("REFRI-SBS-600", "Refrigerador side by side 600 L", "unidad"),
    ("CONGELADOR-VERT-200", "Congelador vertical 200 L", "unidad"),
    ("CONGELADOR-HORIZ-300", "Congelador horizontal 300 L", "unidad"),
    ("FRIGOBAR-90", "Frigobar 90 L", "unidad"),
    ("VINOTECA-24", "Vinoteca 24 botellas", "unidad"),
    ("COCINA-GAS-4Q", "Cocina a gas 4 quemadores", "unidad"),
    ("COCINA-MIXTA-5Q", "Cocina mixta 5 quemadores con horno", "unidad"),
    ("HORNO-EMP-60", "Horno eléctrico empotrable 60 cm", "unidad"),
    ("MICROONDAS-25", "Microondas 25 L", "unidad"),
    ("MICROONDAS-ENCAST", "Microondas encastrable 20 L", "unidad"),
    ("CAMPANA-60", "Campana extractora 60 cm", "unidad"),
    ("ENCIMERA-IND-60", "Encimera de inducción 60 cm", "unidad"),
    ("ENCIMERA-GAS-60", "Encimera a gas 60 cm", "unidad"),
    ("FREIDORA-AIRE-5L", "Freidora de aire 5 L", "unidad"),
    ("LICUADORA-15", "Licuadora 1,5 L", "unidad"),
    ("BATIDORA-MANO", "Batidora de mano 800 W", "unidad"),
    ("BATIDORA-PEDESTAL", "Batidora de pedestal 5 L", "unidad"),
    ("PROCESADOR-ALIM", "Procesador de alimentos 1000 W", "unidad"),
    ("CAFETERA-GOTEO", "Cafetera de goteo 12 tazas", "unidad"),
    ("CAFETERA-CAPS", "Cafetera de cápsulas", "unidad"),
    ("TOSTADORA-2R", "Tostadora 2 rebanadas", "unidad"),
    ("HERVIDOR-17", "Hervidor eléctrico 1,7 L", "unidad"),
    ("ARROCERA-18", "Arrocera eléctrica 1,8 L", "unidad"),
    ("OLLA-PRESION-6L", "Olla a presión eléctrica 6 L", "unidad"),
    ("SANDWICHERA", "Sandwichera antiadherente", "unidad"),
    ("EXPRIMIDOR", "Exprimidor eléctrico de cítricos", "unidad"),
    ("AIRE-SPLIT-12K", "Aire acondicionado split 12.000 BTU", "unidad"),
    ("AIRE-SPLIT-18K", "Aire acondicionado split 18.000 BTU", "unidad"),
    ("AIRE-PORT-12K", "Aire acondicionado portátil 12.000 BTU", "unidad"),
    ("VENTILADOR-PIE", "Ventilador de pie 18 pulgadas", "unidad"),
    ("VENTILADOR-TECHO", "Ventilador de techo con luz", "unidad"),
    ("CALEFACTOR-ELEC", "Calefactor eléctrico 2000 W", "unidad"),
    ("DESHUMIDIF-20L", "Deshumidificador 20 L/día", "unidad"),
    ("HUMIDIFICADOR", "Humidificador ultrasónico 4 L", "unidad"),
    ("TERMO-50L", "Termo eléctrico 50 L", "unidad"),
    ("ASPIRADORA-TRINEO", "Aspiradora de trineo 1800 W", "unidad"),
    ("ASPIRADORA-ROBOT", "Aspiradora robot con mapeo", "unidad"),
    ("ASPIRADORA-VERT", "Aspiradora vertical inalámbrica", "unidad"),
    ("PLANCHA-VAPOR", "Plancha de vapor 2400 W", "unidad"),
    ("PLANCHA-VERT", "Plancha vertical de vapor", "unidad"),
    ("PURIFICADOR-AIRE", "Purificador de aire con filtro HEPA", "unidad"),
]
_APPLIANCE_SUPPLIERS = [
    "Distribuidora Iberelec S.A.",
    "ElectroMayorista del Sur",
    "Importadora Tecnohogar",
    "Comercial Línea Blanca",
    "Grupo Andino de Electrodomésticos",
    "Suministros Pacífico Electro",
    "Mayorista Casa Moderna",
    "Distribuciones Hogar Plus",
]


def _profile(description: str, locations, items, suppliers: list[str], number_prefix: str) -> SeedProfile:
    return SeedProfile(
        description=description,
        locations=locations,
        items=items,
        stock=_stock(items, locations),
        purchase_orders=_purchase_orders(items, suppliers, number_prefix),
    )


PROFILES: dict[str, SeedProfile] = {
    "fruits": _profile(
        "Fruit: 51 items across ambient, cold, ripening and freezer racks, 50 open purchase orders",
        _FRUIT_LOCATIONS,
        _FRUIT_ITEMS,
        _FRUIT_SUPPLIERS,
        "PO-DEMO-",
    ),
    "vegetables": _profile(
        "Vegetables: 52 items across dry store, cold room, root cellar and freezer racks, 50 open orders",
        _VEG_LOCATIONS,
        _VEG_ITEMS,
        _VEG_SUPPLIERS,
        "PO-DEMO-VEG-",
    ),
    "computers": _profile(
        "Computers: 57 items across shelf hall, secure cage, returns bench and cable room, 50 open orders",
        _IT_LOCATIONS,
        _IT_ITEMS,
        _IT_SUPPLIERS,
        "PO-DEMO-IT-",
    ),
    "electrodomesticos": _profile(
        "Electrodomésticos: 60 artículos (TV, lavadoras, refrigeradores, cocina, clima) y 50 órdenes",
        _APPLIANCE_LOCATIONS,
        _APPLIANCE_ITEMS,
        _APPLIANCE_SUPPLIERS,
        "PO-DEMO-ELEC-",
    ),
}
