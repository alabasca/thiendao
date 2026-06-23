"""
╔══════════════════════════════════════════════════════════╗
║  TỌA KÝ — Mount System Data                             ║
╚══════════════════════════════════════════════════════════╝
"""
from __future__ import annotations
from typing import Any

# ══════════════════════════════════════════════════════
#  TỌA KỴ — 9 hệ × 1 mount mỗi hệ
# ══════════════════════════════════════════════════════
TOA_KY: list[dict[str, Any]] = [
    # ── Kim — ATK + Bạo Kích ──────────────────────────────────────────────────
    {
        "id": 0, "he": "kim", "ten": "Kim Lân Kích", "emoji": "🦄",
        "cap": "Linh",
        "mo_ta": "Kỳ lân kim thuộc, mỗi bước chân phát ra âm thanh kim loại vang vọng",
        "effect": {"at_pct": 5.0, "bao_kich": 2.0},
        "passive_effect": "Thép Tâm — Tăng 8% Bạo Kích khi HP > 50%",
        "active_effect": "Kim Sát Trảm — Tấn công phụ 35% AT, bỏ qua 20% DEF (CD 5 lượt)",
        "rate": 8.0,
    },
    # ── Mộc — Drop + EXP ────────────────────────────────────────────────────
    {
        "id": 1, "he": "moc", "ten": "Mộc Linh Lộc", "emoji": "🦌",
        "cap": "Phàm",
        "mo_ta": "Lộc tử linh mộc, mang theo hơi thở sinh sôi của vạn vật",
        "effect": {"drop_rate": 5.0, "exp_pct": 5.0},
        "passive_effect": "Sinh Cơ — Hồi 3% HP tối đa mỗi lượt chiến đấu",
        "active_effect": "Mộc Duyên Trận — Tăng 15% Drop Rate trong 3 lượt (CD 6)",
        "rate": 12.0,
    },
    # ── Thủy — HP + Shield ──────────────────────────────────────────────────
    {
        "id": 2, "he": "thuy", "ten": "Huyền Ngư", "emoji": "🐋",
        "cap": "Phàm",
        "mo_ta": "Cá voi linh khí, lưng rộng như núi, sức mạnh vô biên từ đại dương",
        "effect": {"hp_pct": 6.0, "ho_tam": 100},
        "passive_effect": "Thủy Giáp — Giảm 5% sát thương nhận vào",
        "active_effect": "Hàn Lưu Khiên — Tạo shield 20% HP trong 2 lượt (CD 6)",
        "rate": 12.0,
    },
    # ── Hỏa — AT + Hội Tâm ─────────────────────────────────────────────────
    {
        "id": 3, "he": "hoa", "ten": "Hỏa Phượng Nghi", "emoji": "🦚",
        "cap": "Linh",
        "mo_ta": "Phượng hoàng lửa bất tử, mỗi cánh wing đều rực ngọn lửa vĩnh cửu",
        "effect": {"at_pct": 4.0, "hoi_tam": 200},
        "passive_effect": "Hỏa Linh Thiêu — Tấn công gây thêm 3% ATK sát thương DOT (2 lượt)",
        "active_effect": "Viêm Bùng — Tấn công phụ 30% AT, thiêu đốt 5% HP max (CD 5)",
        "rate": 8.0,
    },
    # ── Thổ — DEF + Kháng Bạo ───────────────────────────────────────────────
    {
        "id": 4, "he": "tho", "ten": "Địa Hành Quy", "emoji": "🐢",
        "cap": "Linh",
        "mo_ta": "Thần quy cổ đại, mai cứng hơn kim cương, mỗi bước rung chuyển đại địa",
        "effect": {"def_pct": 6.0, "khang_bao": 3.0},
        "passive_effect": "Bàn Thạch — Phản 8% sát thương nhận về cho kẻ tấn công",
        "active_effect": "Trấn Ngục Trận — Shield 25% HP trong 3 lượt (CD 7)",
        "rate": 8.0,
    },
    # ── Phong — Tốc độ + Né tránh ───────────────────────────────────────────
    {
        "id": 5, "he": "phong", "ten": "Phong Long Ký", "emoji": "🐲",
        "cap": "Linh",
        "mo_ta": "Rồng gió xanh, bay nhanh như chớp, mỗi cánh quạt tạo ra bão tố",
        "effect": {"def_pct": 3.0, "khang_bao": 2.0, "ho_tam": 80},
        "passive_effect": "Phong Tốc — Tăng 10% né tránh đòn tấn công",
        "active_effect": "Phong Nhãn — Tấn công 2 hit, mỗi hit 20% AT (CD 4)",
        "rate": 8.0,
    },
    # ── Lôi — Bạo Kích cực cao ─────────────────────────────────────────────
    {
        "id": 6, "he": "loi", "ten": "Lôi Đế Kích", "emoji": "⚡",
        "cap": "Tiên",
        "mo_ta": "Sấm sét thiên uy, mỗi bước chân là một tia sét giáng xuống",
        "effect": {"at_pct": 3.0, "bao_kich": 5.0},
        "passive_effect": "Lôi Thể — Tăng 15% Bạo Kích, bạo kích gây choáng 1 lượt",
        "active_effect": "Lôi Đình Kích — Tấn công 50% AT, 100% crit trong 1 lượt (CD 6)",
        "rate": 3.0,
    },
    # ── Quang — EXP + Drop ───────────────────────────────────────────────────
    {
        "id": 7, "he": "quang", "ten": "Minh Nguyệt Lộc", "emoji": "🐇",
        "cap": "Phàm",
        "mo_ta": "Thỏ nguyệt thần, mang theo ánh sáng tinh khiết và may mắn vô biên",
        "effect": {"exp_pct": 6.0, "drop_rate": 4.0},
        "passive_effect": "Quang Chiếu — Tăng 10% EXP nhận được từ mọi nguồn",
        "active_effect": "Thiên Quang Trận — Hồi 5% HP + AT +10% trong 3 lượt (CD 5)",
        "rate": 12.0,
    },
    # ── Ám — Sát thương boss ─────────────────────────────────────────────
    {
        "id": 8, "he": "am", "ten": "Hắc Diệm Sư", "emoji": "🐉",
        "cap": "Tiên",
        "mo_ta": "Sư tử bóng tối, toàn thân bao phủ ngọn lửa hắc ám đốt cháy linh hồn",
        "effect": {"bao_kich": 4.0, "at_pct": 2.0},
        "passive_effect": "Ám Sát — Tăng 20% sát thương lên boss",
        "active_effect": "Hắc Ám Xuyên — Tấn công 40% AT, xuyên 30% DEF (CD 5)",
        "rate": 3.0,
    },
]

TOA_KY_BY_ID: dict[int, dict[str, Any]]  = {tk["id"]: tk for tk in TOA_KY}
TOA_KY_BY_HE: dict[str, dict[str, Any]] = {tk["he"]: tk for tk in TOA_KY}

# Hệ số buff theo level (per level)
TOA_KY_LEVEL_MULT: dict[int, float] = {
    1: 1.0, 2: 1.2, 3: 1.5, 4: 1.8, 5: 2.2,
    6: 2.7, 7: 3.2, 8: 3.8, 9: 4.5, 10: 5.5,
}

# Yêu cầu cảnh giới để nâng cấp mount lên level nhất định
TOA_KY_LEVELUP_CG_YEU_CAU: dict[int, int] = {
    1: 0, 2: 0, 3: 0, 4: 1, 5: 2,
    6: 3, 7: 4, 8: 5, 9: 6, 10: 7,
}

# ══════════════════════════════════════════════════════
#  NGUYÊN LIỆU NÂNG CẤP TỌA KỴ
# ══════════════════════════════════════════════════════
TOA_KY_NGUYEN_LIEU: list[dict[str, Any]] = [
    {"id": "long_tam",     "ten": "Long Tàm",       "emoji": "🐉", "gia": 200},
    {"id": "tien_linh",    "ten": "Thiên Linh Thạch", "emoji": "💎", "gia": 500},
    {"id": "huyet_nguyet", "ten": "Huyết Nguyệt Châu","emoji": "🔴", "gia": 1000},
    {"id": "van_khoai",    "ten": "Vân Khối",        "emoji": "☁️", "gia": 2000},
    {"id": "tien_mai",     "ten": "Tiên Mai",        "emoji": "🌸", "gia": 5000},
]

TOA_KY_NL_BY_ID: dict[str, dict[str, Any]] = {nl["id"]: nl for nl in TOA_KY_NGUYEN_LIEU}

# Chi phí nâng cấp (key = level đích)
TOA_KY_LEVELUP_COST: dict[int, dict[str, int]] = {
    2:  {"long_tam": 5},
    3:  {"long_tam": 10, "tien_linh": 3},
    4:  {"long_tam": 20, "tien_linh": 8},
    5:  {"tien_linh": 15, "huyet_nguyet": 5},
    6:  {"tien_linh": 25, "huyet_nguyet": 10, "van_khoai": 3},
    7:  {"huyet_nguyet": 20, "van_khoai": 8},
    8:  {"van_khoai": 15, "tien_mai": 5},
    9:  {"van_khoai": 25, "tien_mai": 10},
    10: {"tien_mai": 20},
}

# ══════════════════════════════════════════════════════
#  BANNER GACHA
# ══════════════════════════════════════════════════════
TOA_KY_BANNER = {
    "ten": "Bình Dân Tọa Kỵ",
    "mo_ta": "Banner thường — cơ hội nhận tọa kỵ ngẫu nhiên",
    "chi_phi_10": 50000,
    "chi_phi_10": 50000,
    "rotation_hours": 12,
    "featured_rate": 50.0,
    "rates": {
        "Phàm": 70.0,
        "Linh": 25.0,
        "Tiên": 4.5,
        "Thần": 0.5,
    },
    "pity_soft": 75,   # soft pity start
    "pity_hard": 90,   # hard pity guarantee
}



# Rate pool theo rarity
TOA_KY_RARITY_POOL: dict[str, list[int]] = {
    "Phàm": [1, 2, 7],           # Mộc Linh Lộc, Huyền Ngư, Minh Nguyệt Lộc
    "Linh": [0, 3, 4, 5],        # Kim Lân, Hỏa Phượng, Địa Hành Quy, Phong Long
    "Tiên": [6, 8],              # Lôi Đế, Hắc Diệm Sư
    "Thần": [],                   # Chưa có mount Thần cấp (mở rộng sau)
}

# ══════════════════════════════════════════════════════
#  TINH HOA TỌA KỴ (duplicate → currency nâng cấp)
# ══════════════════════════════════════════════════════
TOA_KY_DUPE_TINH_HOA: dict[str, int] = {
    "Phàm": 10,
    "Linh": 30,
    "Tiên": 80,
    "Thần": 200,
}

# ══════════════════════════════════════════════════════
#  BÍ CẢNH TỌA KỴ — 5 level BC mới
# ══════════════════════════════════════════════════════
TOA_KY_BI_CANH: list[dict[str, Any]] = [
    # BC0 — Mount Lv 1+
    {
        "id": 0, "ten": "Rồng Biển", "emoji": "🌊",
        "mo_ta": "Đại dương sâu thẳm, nơi cư ngụ của các linh thú thủy hệ",
        "cap_toi_thieu": 1,
        "the_luc_phi": 15,
        "phong_thuong": [
            {"ten": "Hải Tặc",   "emoji": "🏴", "hp": 3500,  "at": 90,   "df": 28,
             "exp_min": 120, "exp_max": 200, "lt_min": 70, "lt_max": 120,
             "nl_drop": ["long_tam"], "nl_rate": 0.15},
            {"ten": "Hải Quái",  "emoji": "🦑", "hp": 4500,  "at": 110,  "df": 35,
             "exp_min": 150, "exp_max": 250, "lt_min": 90, "lt_max": 140,
             "nl_drop": ["long_tam"], "nl_rate": 0.18},
            {"ten": "Hải Sư",    "emoji": "🦁", "hp": 5500,  "at": 135,  "df": 42,
             "exp_min": 180, "exp_max": 300, "lt_min": 110, "lt_max": 170,
             "nl_drop": ["long_tam", "tien_linh"], "nl_rate": 0.12},
        ],
        "boss": {
            "ten": "Thủy Long Vương", "emoji": "🐉",
            "hp": 10000, "at": 220, "df": 55,
            "exp_min": 500, "exp_max": 850, "lt_min": 300, "lt_max": 500,
            "nl_drop": ["long_tam", "tien_linh"], "nl_rate": 0.30,
            "mo_ta": "Thủy Long Vương trấn giữ đại dương, vảy cứng hơn thép!",
        },
    },
    # BC1 — Mount Lv 3+
    {
        "id": 1, "ten": "Hỏa Diệm Sơn", "emoji": "🌋",
        "mo_ta": "Núi lửa nóng bỏng, dung nham chảy thành sông",
        "cap_toi_thieu": 3,
        "the_luc_phi": 20,
        "phong_thuong": [
            {"ten": "Hỏa Tinh",  "emoji": "🔥", "hp": 8000,  "at": 250,  "df": 65,
             "exp_min": 300, "exp_max": 500, "lt_min": 180, "lt_max": 280,
             "nl_drop": ["long_tam", "tien_linh"], "nl_rate": 0.15},
            {"ten": "Nham Thạch", "emoji": "🗿", "hp": 10500, "at": 320,  "df": 85,
             "exp_min": 380, "exp_max": 640, "lt_min": 230, "lt_max": 350,
             "nl_drop": ["tien_linh", "huyet_nguyet"], "nl_rate": 0.12},
            {"ten": "Hỏa Yêu",   "emoji": "👹", "hp": 13000, "at": 400,  "df": 105,
             "exp_min": 470, "exp_max": 780, "lt_min": 280, "lt_max": 430,
             "nl_drop": ["tien_linh", "huyet_nguyet"], "nl_rate": 0.15},
        ],
        "boss": {
            "ten": "Hỏa Diệm Thú", "emoji": "🔥",
            "hp": 22000, "at": 550, "df": 130,
            "exp_min": 1200, "exp_max": 2000, "lt_min": 700, "lt_max": 1100,
            "nl_drop": ["tien_linh", "huyet_nguyet"], "nl_rate": 0.28,
            "mo_ta": "Hỏa Diệm Thú — sinh vật lửa vạn năm, mỗi hơi thở là núi lửa!",
        },
    },
    # BC2 — Mount Lv 5+
    {
        "id": 2, "ten": "Băng Nguyên", "emoji": "❄️",
        "mo_ta": "Đồng băng vĩnh cửu, nhiệt độ xuống âm vô cùng",
        "cap_toi_thieu": 5,
        "the_luc_phi": 25,
        "phong_thuong": [
            {"ten": "Băng Tinh",   "emoji": "🧊", "hp": 18000, "at": 650,  "df": 170,
             "exp_min": 700, "exp_max": 1150, "lt_min": 420, "lt_max": 640,
             "nl_drop": ["tien_linh", "huyet_nguyet", "van_khoai"], "nl_rate": 0.12},
            {"ten": "Hàn Băng Lang","emoji": "🐺", "hp": 23000, "at": 820,  "df": 210,
             "exp_min": 880, "exp_max": 1460, "lt_min": 530, "lt_max": 800,
             "nl_drop": ["huyet_nguyet", "van_khoai"], "nl_rate": 0.14},
            {"ten": "Băng Phượng",  "emoji": "🦅", "hp": 28000, "at": 1000, "df": 260,
             "exp_min": 1080, "exp_max": 1800, "lt_min": 650, "lt_max": 980,
             "nl_drop": ["huyet_nguyet", "van_khoai"], "nl_rate": 0.16},
        ],
        "boss": {
            "ten": "Băng Huyền Nữ", "emoji": "👸",
            "hp": 45000, "at": 1400, "df": 320,
            "exp_min": 3000, "exp_max": 5000, "lt_min": 1800, "lt_max": 2700,
            "nl_drop": ["huyet_nguyet", "van_khoai", "tien_mai"], "nl_rate": 0.25,
            "mo_ta": "Băng Huyền Nữ — nữ thần băng giá, một cái nhìn đông cứng vạn vật!",
        },
    },
    # BC3 — Mount Lv 7+
    {
        "id": 3, "ten": "Lôi Động Thiên", "emoji": "⛈️",
        "mo_ta": "Bầu trời sấm sét vĩnh cửu, mỗi tia sét phá hủy cả núi non",
        "cap_toi_thieu": 7,
        "the_luc_phi": 30,
        "phong_thuong": [
            {"ten": "Lôi Tinh",    "emoji": "⚡", "hp": 35000, "at": 1500, "df": 380,
             "exp_min": 1800, "exp_max": 3000, "lt_min": 1080, "lt_max": 1620,
             "nl_drop": ["van_khoai", "tien_mai"], "nl_rate": 0.12},
            {"ten": "Thiên Lôi Thú","emoji": "🌩️", "hp": 45000, "at": 1900, "df": 480,
             "exp_min": 2300, "exp_max": 3800, "lt_min": 1380, "lt_max": 2070,
             "nl_drop": ["van_khoai", "tien_mai"], "nl_rate": 0.15},
            {"ten": "Lôi Đế Binh",  "emoji": "🛐", "hp": 55000, "at": 2300, "df": 580,
             "exp_min": 2800, "exp_max": 4700, "lt_min": 1680, "lt_max": 2520,
             "nl_drop": ["van_khoai", "tien_mai"], "nl_rate": 0.18},
        ],
        "boss": {
            "ten": "Lôi Trụ Thiên", "emoji": "🌩️",
            "hp": 85000, "at": 3200, "df": 700,
            "exp_min": 8000, "exp_max": 13000, "lt_min": 5000, "lt_max": 7500,
            "nl_drop": ["van_khoai", "tien_mai"], "nl_rate": 0.30,
            "mo_ta": "Lôi Tr柱 Thiên — cột sét trời giáng, sức mạnh phá hủy cả tiên giới!",
        },
    },
    # BC4 — Mount Lv 9+
    {
        "id": 4, "ten": "Tiên Giới Môn", "emoji": "🌌",
        "mo_ta": "Cổng tiên giới mở ra, linh khí nồng đậm gấp vạn lần nhân gian",
        "cap_toi_thieu": 9,
        "the_luc_phi": 40,
        "phong_thuong": [
            {"ten": "Tiên Linh",     "emoji": "✨", "hp": 60000, "at": 2800, "df": 700,
             "exp_min": 4500, "exp_max": 7500, "lt_min": 2700, "lt_max": 4050,
             "nl_drop": ["tien_mai"], "nl_rate": 0.20},
            {"ten": "Thiên Binh",     "emoji": "⚔️", "hp": 78000, "at": 3500, "df": 880,
             "exp_min": 5800, "exp_max": 9700, "lt_min": 3480, "lt_max": 5220,
             "nl_drop": ["tien_mai"], "nl_rate": 0.25},
            {"ten": "Tiên Thú",       "emoji": "🐾", "hp": 95000, "at": 4200, "df": 1050,
             "exp_min": 7200, "exp_max": 12000, "lt_min": 4320, "lt_max": 6480,
             "nl_drop": ["tien_mai"], "nl_rate": 0.30},
        ],
        "boss": {
            "ten": "Tiên Đế", "emoji": "👑",
            "hp": 150000, "at": 5500, "df": 1200,
            "exp_min": 18000, "exp_max": 30000, "lt_min": 11000, "lt_max": 16500,
            "nl_drop": ["tien_mai"], "nl_rate": 0.40,
            "mo_ta": "Tiên Đế — chúa tể tiên giới, sức mạnh vượt ngoài tầm hiểu biết!",
        },
    },
]

TOA_KY_BI_CANH_BY_ID: dict[int, dict[str, Any]] = {bc["id"]: bc for bc in TOA_KY_BI_CANH}
