"""
╔══════════════════════════════════════════════════════╗
║  QUỶ CỐC BÁT HOANG — CONFIG & GAME DATA             ║
╚══════════════════════════════════════════════════════╝
"""
from __future__ import annotations
from typing import Any

import os
from dotenv import load_dotenv
from utils.bot_emojis import (
    E_HP_START, E_HP_MID, E_HP_END,
    E_HP_START_E, E_HP_MID_E, E_HP_END_E,
    E_DAN_DUOC,
)

from data.game_data import *
from data.bi_canh_data import BI_CANH, BI_CANH_BY_ID
from data.boss_data import BOSS_THE_GIOI, BOSS_SPAWN_HOURS_VN

load_dotenv()  # Tự động đọc file .env

# ══════════════════════════════════════════════════════
#  BOT CONFIG
# ══════════════════════════════════════════════════════
_raw_token = os.getenv("BOT_TOKEN", "")
if not _raw_token or _raw_token == "YOUR_TOKEN_HERE":
    raise RuntimeError(
        "Thiếu biến môi trường BOT_TOKEN! "
        "Hãy tạo file .env hoặc set biến môi trường trước khi chạy bot."
    )
TOKEN: str = _raw_token
OWNER_ID: int = int(os.getenv("OWNER_ID", "0"))
OWNER_IDS: set[int] = {OWNER_ID, 1007631986623524965}
# Channel để bot gửi thông báo boss bị đánh bại / biến mất (set ID thực trong .env)
BOSS_ANNOUNCE_CHANNEL_ID: int = int(os.getenv("BOSS_ANNOUNCE_CHANNEL_ID", "0"))

# ══════════════════════════════════════════════════════
#  FUNCTIONS (depend on game_data constants)
# ══════════════════════════════════════════════════════
def get_cg_ten(cg_id: int, cap: int) -> str:
    cg: dict[str, Any] = CANH_GIOI[min(cg_id, len(CANH_GIOI) - 1)]
    return f"{CAP_NHO[min(cap-1,2)]} {cg['ten']}"

def get_cg(cg_id: int) -> dict[str, Any]:
    return CANH_GIOI[min(cg_id, len(CANH_GIOI) - 1)]

# Bảng EXP từng giai đoạn: [sơ kì, trung kì, hậu kì]
_EXP_TABLE: list[list[int]] = [
    [17544,    22806,     19298],       # 0  Luyện Khí
    [53712,    69824,     59082],       # 1  Trúc Cơ
    [124272,   161552,    136698],      # 2  Kết Tinh
    [336800,   437840,    370480],      # 3  Kim Đan
    [919800,   1195740,   1011780],     # 4  Cụ Linh
    [2882520,  3747276,   3170772],     # 5  Nguyên Anh
    [5552000,  7217600,   6107200],     # 6  Hóa Thần
    [11856328, 15413226,  13041960],    # 7  Ngộ Đạo
    [29425424, 38253050,  32367966],    # 8  Vũ Hóa
    [44820000, 58266000,  999999999],   # 9  Đăng Tiên (hậu kì chưa mở)
]

def exp_can_thiet(cg_id: int, cap: int) -> int:
    """Trả về tu vi cần để đột phá lên giai đoạn tiếp theo (cap: 1=sơ, 2=trung, 3=hậu)."""
    if cg_id < 0 or cg_id >= len(_EXP_TABLE):
        return 999999999
    row = _EXP_TABLE[cg_id]
    idx = max(0, min(cap - 1, len(row) - 1))
    return row[idx]

# Base stats — calibrated để buộc người chơi cần công pháp
# 0 CP thua ~10-20%, 10 CP thắng ~98%+, CG+1 farm tầng dưới 100%
_AT_BASE: list[int] = [22, 64, 202, 433, 842, 2778, 6028, 8181, 9307, 10906]
_DF_BASE: list[int] = [50, 225, 778, 1700, 3333, 11035, 23999, 32611, 37130, 43531]
_HP_BASE: list[int] = [598, 2183, 7271, 18178, 45445, 101780, 221169, 300404, 341926, 400795]

def cong_cong_thuc(cg_id: int, cap: int) -> int:
    base = _AT_BASE[min(cg_id, 9)]
    return int(base * (1 + cap * 0.05))

def thu_cong_thuc(cg_id: int, cap: int) -> int:
    base = _DF_BASE[min(cg_id, 9)]
    return int(base * (1 + cap * 0.05))

def hp_max_cong_thuc(cg_id: int, cap: int) -> int:
    base = _HP_BASE[min(cg_id, 9)]
    return int(base * (1 + cap * 0.05))

def random_linh_can_khoi_dau() -> list[str]:
    """Random linh căn khi tạo hồ sơ mới.
    Trả về list gồm 1-5 linh căn không trùng nhau.
    Tỉ lệ: 1 căn = phần còn lại, 2 = 1%, 3 = 0.5%, 4 = 0.3%, 5 = 0.07%
    Mỗi căn co_ban xác suất đều 20%, hiếm/sieu_hiem không drop ở đây.
    """
    import random as _r
    roll = _r.random() * 100  # 0–100
    if roll < 0.07:
        so_can = 5
    elif roll < 0.37:   # 0.07 + 0.30
        so_can = 4
    elif roll < 0.87:   # + 0.50
        so_can = 3
    elif roll < 1.87:   # + 1.00
        so_can = 2
    else:
        so_can = 1
    pool = list(LINH_CAN_CO_BAN)
    _r.shuffle(pool)
    return pool[:so_can]

def random_linh_can_co_ban() -> str:
    """Giữ tương thích ngược — trả về 1 linh căn cơ bản ngẫu nhiên."""
    import random
    return random.choice(LINH_CAN_CO_BAN)

def random_the_chat() -> str:
    """Random thể chất theo tỉ lệ rate."""
    import random
    r: float = random.uniform(0, sum(tc["rate"] for tc in THE_CHAT))
    cum: float = 0.0
    for tc in THE_CHAT:
        cum += tc["rate"]
        if r < cum:
            return tc["id"]
    return THE_CHAT[-1]["id"]

def get_quan_he_cap(diem: int) -> dict:
    if diem >= 0:
        cap = {"diem": 0, "ten": "Xa Lạ", "emoji": "👤", "ket_giao": []}
        for m in QUAN_HE_MOC_DUONG:
            if diem >= m["diem"]: cap = m
        return cap
    else:
        cap = {"diem": 0, "ten": "Xa Lạ", "emoji": "👤"}
        for m in QUAN_HE_MOC_AM:
            if diem <= m["diem"]: cap = m
        return cap

# ══════════════════════════════════════════════════════
#  COOLDOWNS (giây)
# ══════════════════════════════════════════════════════
CD_TU_LUYEN    = 3600
CD_DOT_PHA     = 7200
CD_KHAI_HOANG  = 86400
CD_BI_CANH     = 1800
CD_DIEM_DANH   = 86400

# ══════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════
def fmt(n: int) -> str:
    return f"{int(n):,}".replace(",", ".")

def bar(val, mx, length=12) -> str:
    if mx <= 0: return "█" * length
    p = min(val / mx, 1.0)
    f = int(p * length)
    return "█" * f + "░" * (length - f)

def boss_bar(val, mx) -> str:
    if mx <= 0: return "█" * 10
    cuc = max(0, min(10, round(val / mx * 10)))
    return "█" * cuc + "░" * (10 - cuc)

HP_START    = E_HP_START
HP_START_E  = E_HP_START_E
HP_MID      = E_HP_MID
HP_MID_E    = E_HP_MID_E
HP_END      = E_HP_END
HP_END_E    = E_HP_END_E

def emoji_hp_bar(val, mx, length=10) -> str:
    if mx <= 0:
        return HP_START + HP_MID * (length - 2) + HP_END
    filled = max(0, min(length, round(val / mx * length)))
    bar_parts = []
    for i in range(length):
        is_filled = i < filled
        if i == 0:
            bar_parts.append(HP_START if is_filled else HP_START_E)
        elif i == length - 1:
            bar_parts.append(HP_END if is_filled else HP_END_E)
        else:
            bar_parts.append(HP_MID if is_filled else HP_MID_E)
    return "".join(bar_parts)

BOSS_HP_BY_CG: dict[int, int] = {
    3: 150_000_000,
    4: 300_000_000,
    5: 600_000_000,
    6: 900_000_000,
    9: 6_000_000_000,
}

def fmt_cd(giay: int) -> str:
    if giay <= 0: return "✅ Sẵn sàng"
    h = giay // 3600; m = (giay % 3600) // 60; s = giay % 60
    parts = []
    if h: parts.append(f"{h}h")
    if m: parts.append(f"{m}p")
    if s and not h: parts.append(f"{s}s")
    return "⏳ " + " ".join(parts)

# ══════════════════════════════════════════════════════
#  MISC
# ══════════════════════════════════════════════════════
EMOJI_DAN_DUOC = E_DAN_DUOC

BUFF_LABELS: dict[str, str] = {
    "exp":        "Tu vi tu luyện",
    "cong":       "Sát thương",
    "linh_thach": "Linh thạch",
    "hp":         "Sinh lực tối đa",
}
