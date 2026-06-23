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
from data.toa_ky_data import (
    TOA_KY, TOA_KY_BY_ID, TOA_KY_BY_HE,
    TOA_KY_LEVEL_MULT, TOA_KY_LEVELUP_CG_YEU_CAU,
    TOA_KY_NGUYEN_LIEU, TOA_KY_NL_BY_ID, TOA_KY_LEVELUP_COST,
    TOA_KY_BANNER,
    TOA_KY_RARITY_POOL, TOA_KY_DUPE_TINH_HOA,
    TOA_KY_BI_CANH, TOA_KY_BI_CANH_BY_ID,
)

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

# ══════════════════════════════════════════════════════
#  QUÁI SCALE THEO TRƯNG SINH
# ══════════════════════════════════════════════════════
TRUNG_SINH_MONSTER_SCALE = 0.15  # +15% HP/ATK/DEF per rebirth

def monster_scale(so_lan_ts: int) -> float:
    """Hệ số scale quái theo số lần trùng sinh."""
    return 1.0 + so_lan_ts * TRUNG_SINH_MONSTER_SCALE

# ══════════════════════════════════════════════════════
#  Ý CẢNH — SKILL TREE
# ══════════════════════════════════════════════════════
Y_CANH_DIEM_CO_BAN = 5
Y_CANH_DIEM_MOI_TS = 3

def y_canh_diem_toi_da(so_lan_ts: int) -> int:
    """Điểm skill tree tối đa = 5 + (số lần trùng sinh × 3)."""
    return Y_CANH_DIEM_CO_BAN + so_lan_ts * Y_CANH_DIEM_MOI_TS

DA_NGO_DAO_ID = "da_ngo_dao"
DA_NGO_DAO_GIA = 5000  # linh thạch per stone
DA_NGO_DAO_DAILY_LIMIT = 100  # giới hạn mua/ngày

DA_RESET_SKILL_TREE_ID = "da_reset_skill_tree"
DA_RESET_SKILL_TREE_GIA = 20000  # linh thạch
DA_RESET_SKILL_TREE_DAILY_LIMIT = 5  # giới hạn mua/ngày

Y_CANH_NHANH = [
    {
        "id": "hoa_diem_tam_muoi", "ten": "Hỏa Diệm Tam Muội", "emoji": "🔥",
        "mo_ta": "Con đường tấn công, tăng ATK và Bạo Kích",
        "nodes": [
            {"id": "tam_muoi_chan_hoa", "ten": "Tam Muội Chân Hỏa", "max_lv": 5, "cost": [5,10,15,25,40], "effect": {"at_pct": 2}},
            {"id": "liem_tram_phan_hoa", "ten": "Liêm Trảm Phẫn Hỏa", "max_lv": 5, "cost": [5,10,15,25,40], "effect": {"bao_kich": 1.5}},
            {"id": "thien_hoa_phe_hon", "ten": "Thiên Hỏa Phệ Hồn", "max_lv": 3, "cost": [15,30,50], "effect": {"crit_dmg": 5}},
            {"id": "dien_linh_thuat", "ten": "Diệm Linh Thuật", "max_lv": 3, "cost": [20,40,60], "effect": {"hut_mau_crit": 2}},
            {"id": "hoa_long_chan_y", "ten": "Hỏa Long Chân Ý", "max_lv": 1, "cost": [100], "effect": {"at_pct": 15}},
        ]
    },
    {
        "id": "huyen_vu_chan_thuat", "ten": "Huyền Vũ Chân Thuật", "emoji": "🛡️",
        "mo_ta": "Con đường phòng thủ, tăng HP và DEF",
        "nodes": [
            {"id": "huyen_quy_ho_the", "ten": "Huyền Quy Hộ Thể", "max_lv": 5, "cost": [5,10,15,25,40], "effect": {"hp_pct": 3}},
            {"id": "vu_giap_thien_thanh", "ten": "Vũ Giáp Thiên Thành", "max_lv": 5, "cost": [5,10,15,25,40], "effect": {"def_pct": 2}},
            {"id": "xa_giap_bat_hoai", "ten": "Xà Giáp Bất Hoại", "max_lv": 3, "cost": [15,30,50], "effect": {"khang_bao": 2}},
            {"id": "thuy_nguyen_hoi_thien", "ten": "Thủy Nguyên Hồi Thiên", "max_lv": 3, "cost": [20,40,60], "effect": {"hoi_sinh_luc": 1}},
            {"id": "huyen_vu_chan_than", "ten": "Huyền Vũ Chân Thân", "max_lv": 1, "cost": [100], "effect": {"hp_pct": 20, "def_pct": 10}},
        ]
    },
    {
        "id": "loi_phan_thien_co", "ten": "Lôi Phẫn Thiên Cơ", "emoji": "⚡",
        "mo_ta": "Con đường linh lực, tăng kỹ năng và hồi phục",
        "nodes": [
            {"id": "loi_dong_cuu_thien", "ten": "Lôi Động Cửu Thiên", "max_lv": 5, "cost": [5,10,15,25,40], "effect": {"linh_luc_pct": 3}},
            {"id": "phan_loi_chan_hon", "ten": "Phẫn Lôi Chấn Hồn", "max_lv": 5, "cost": [5,10,15,25,40], "effect": {"hoi_tam": 2}},
            {"id": "thien_loi_phat_toi", "ten": "Thiên Lôi Phạt Tội", "max_lv": 3, "cost": [15,30,50], "effect": {"ho_tam": 2}},
            {"id": "loi_thuat_dien_thien", "ten": "Lôi Thuật Diên Thiên", "max_lv": 3, "cost": [20,40,60], "effect": {"cd_giam": 1.5}},
            {"id": "loi_phan_chan_y", "ten": "Lôi Phẫn Chân Ý", "max_lv": 1, "cost": [100], "effect": {"linh_luc_pct": 20}},
        ]
    },
    {
        "id": "moc_duyen_sinh_co", "ten": "Mộc Duyên Sinh Cơ", "emoji": "🌿",
        "mo_ta": "Con đường sinh trưởng, tăng EXP và Drop",
        "nodes": [
            {"id": "moc_duyen_sinh_truong", "ten": "Mộc Duyên Sinh Trưởng", "max_lv": 5, "cost": [5,10,15,25,40], "effect": {"exp_pct": 2}},
            {"id": "thao_moc_huu_tinh", "ten": "Thảo Mộc Hữu Tình", "max_lv": 5, "cost": [5,10,15,25,40], "effect": {"drop_rate": 2}},
            {"id": "sinh_co_vo_tan", "ten": "Sinh Cơ Vô Tận", "max_lv": 3, "cost": [15,30,50], "effect": {"the_luc_hoi": 1}},
            {"id": "thien_dia_quy_nguyen", "ten": "Thiên Địa Quy Nguyên", "max_lv": 3, "cost": [20,40,60], "effect": {"lt_nhan": 3}},
            {"id": "moc_duyen_chan_y", "ten": "Mộc Duyên Chân Ý", "max_lv": 1, "cost": [100], "effect": {"exp_pct": 15, "drop_rate": 10}},
        ]
    },
]

# Build lookup
Y_CANH_BY_NHANH = {n["id"]: n for n in Y_CANH_NHANH}
Y_CANH_ALL_NODES = {}
for _n in Y_CANH_NHANH:
    for _nd in _n["nodes"]:
        Y_CANH_ALL_NODES[_nd["id"]] = {**_nd, "nhanh_id": _n["id"]}

TRAN_DAO = [
    {"id": "tran_liet_hoa", "ten": "Trận Liệt Hỏa", "emoji": "🔥",
     "mo_ta": "Tấn công mạnh, hy sinh máu",
     "buff": {"at_pct": 25}, "debuff": {"hp_pct": -10}, "unlock": None},
    {"id": "tran_huyen_vu", "ten": "Trận Huyền Vũ", "emoji": "🛡️",
     "mo_ta": "Phòng thủ vững, hy sinh tấn công",
     "buff": {"hp_pct": 30, "def_pct": 15}, "debuff": {"at_pct": -10},
     "unlock": {"nhanh": "huyen_vu_chan_thuat", "node": "huyen_quy_ho_the"}},
    {"id": "tran_bach_ho", "ten": "Trận Bạch Hổ", "emoji": "🐯",
     "mo_ta": "Tấn công + bạo kích, hy sinh phòng ngự",
     "buff": {"at_pct": 20, "bao_kich": 10}, "debuff": {"def_pct": -10},
     "unlock": {"nhanh": "hoa_diem_tam_muoi", "node": "tam_muoi_chan_hoa"}},
    {"id": "tran_phong_loi", "ten": "Trận Phong Lôi", "emoji": "⛈️",
     "mo_ta": "Linh lực + kỹ năng nhanh, hy sinh máu",
     "buff": {"linh_luc_pct": 20, "cd_giam": 15}, "debuff": {"hp_pct": -10},
     "unlock": {"nhanh": "loi_phan_thien_co", "node": "loi_dong_cuu_thien"}},
]
TRAN_DAO_BY_ID = {t["id"]: t for t in TRAN_DAO}
