from __future__ import annotations
from typing import Any

from utils.bot_emojis import (
    E_LUYEN_KHI, E_TRUC_CO, E_KET_TINH, E_KIM_DAN, E_TU_LINH,
    E_NGUYEN_ANH, E_HOA_THAN, E_NGO_DAO, E_VU_HOA, E_DANG_TIEN,
    E_DAN_TRUC_CO, E_DAN_KIM_DAN, E_DAN_CU_LINH, E_DAN_NGUYEN_ANH,
    E_DAN_HOA_THAN, E_DAN_VU_HOA, E_DAN_NGO_DAO, E_DAN_DANG_TIEN,
    E_HOA_LINH_CAN, E_THUY_LINH_CAN, E_MOC_LINH_CAN,
    E_THO_LINH_CAN, E_PHONG_LINH_CAN, E_LOI_LINH_CAN,
    E_KIM_LINH_CAN, E_AM_LINH_CAN, E_QUANG_LINH_CAN,
    E_MANH_HOA, E_MANH_THUY, E_MANH_THO, E_MANH_MOC, E_MANH_KIM,
    E_MANH_LOI, E_MANH_PHONG, E_MANH_AM, E_MANH_QUANG,
    E_QUA_HOA, E_QUA_THUY, E_QUA_THO, E_QUA_MOC, E_QUA_KIM,
    E_QUA_LOI, E_QUA_PHONG, E_QUA_AM, E_QUA_QUANG,
    E_HOANNGUYEN, E_HONDONCHITUC, E_HONDONCHITUC_HIEM, E_HONDONLINHTUC,
    E_HOPLINH, E_KETTHAN, E_LUYENTHEDAN_HIEM, E_LUYENTHEDAN_THUONG,
    E_NGUNGTHAN, E_TAPKHI, E_TAYTUY_HIEM, E_TAYTUY_THUONG,
    E_THANGNGUYEN, E_THANHTINHLINHTUC, E_THONGMACH, E_THUANMACH,
    E_TIENTHIENNHATKHI_HIEM, E_TIENTHIENNHATKHI_THUONG,
    E_TRUHUYET, E_TUKHI, E_UANHUYET, E_DUNGLINH,
)

# ══════════════════════════════════════════════════════
#  CẢNH GIỚI
# ══════════════════════════════════════════════════════
CANH_GIOI: list[dict[str, Any]] = [
    {"id": 0, "ten": "Luyện Khí",  "emoji": E_LUYEN_KHI,   "mau": 0x6BCB77, "cap": 3},
    {"id": 1, "ten": "Trúc Cơ",   "emoji": E_TRUC_CO,      "mau": 0x4D96FF, "cap": 3},
    {"id": 2, "ten": "Kết Tinh",  "emoji": E_KET_TINH,     "mau": 0x00FFFF, "cap": 3},
    {"id": 3, "ten": "Kim Đan",   "emoji": E_KIM_DAN,      "mau": 0xFFD93D, "cap": 3},
    {"id": 4, "ten": "Cụ Linh",   "emoji": E_TU_LINH,      "mau": 0xFF6B35, "cap": 3},
    {"id": 5, "ten": "Nguyên Anh","emoji": E_NGUYEN_ANH,   "mau": 0xC77DFF, "cap": 3},
    {"id": 6, "ten": "Hóa Thần",  "emoji": E_HOA_THAN,     "mau": 0x7B2FBE, "cap": 3},
    {"id": 7, "ten": "Ngộ Đạo",   "emoji": E_NGO_DAO,      "mau": 0xFCE38A, "cap": 3},
    {"id": 8, "ten": "Vũ Hóa",    "emoji": E_VU_HOA,       "mau": 0xFF69B4, "cap": 3},
    {"id": 9, "ten": "Đăng Tiên", "emoji": E_DANG_TIEN,    "mau": 0xFFD700, "cap": 3},
    {"id": 10, "ten": "Vấn Đỉnh Tiên Tôn", "emoji": "✨",  "mau": 0xFFFFFF, "cap": 1},
]
CAP_NHO: list[str] = ["Sơ Kì", "Trung Kì", "Hậu Kì"]

# Hệ số thưởng điểm danh theo cảnh giới (index = canh_gioi id)
DIEM_DANH_HE_SO: list[float] = [1.0, 1.5, 2.0, 2.5, 3.5, 4.5, 5.0, 5.5, 7.0, 10.0, 15.0]

# Tu vi cần tích lũy để thử đột phá Vấn Đỉnh Tiên Tôn (không cần đan)
VAN_DINH_TUVI_YEU_CAU = 999_999_999

# ══════════════════════════════════════════════════════
#  LINH CĂN NGUYÊN TỐ
#  loai: "co_ban" → random khi tạo hồ sơ (5 căn, 20% mỗi loại)
#         "hiem"  → chỉ kiếm qua mảnh drop trong game
#  Passive lớp 1: luôn active (flat)
#  Buff lớp 2:    cộng dồn mỗi lần đột phá cảnh giới LỚN
# ══════════════════════════════════════════════════════
LINH_CAN: list[dict[str, Any]] = [
    # ── CĂN CƠ BẢN (5 loại — random khi tạo nhân vật) ─────────────────────────
    # Hỏa: chuyên tấn công, nhưng bớt AT% để không stack quá mạnh với THE_CHAT
    {
        "id": "hoa", "ten": "Hỏa Linh Căn", "emoji": E_HOA_LINH_CAN,
        "mau": 0xE05A20, "loai": "co_ban",
        "passive": {"at_flat": 25, "at_pct": 3.5, "bao_kich": 1.5},
        "dot_pha_buff": {"at_pct": 2.0},
        "chuc_mung": f"{E_HOA_LINH_CAN} Hỏa linh căn — con đường sát thương đã mở!",
    },
    # Thủy: chuyên sinh tồn — HP + hộ tâm (giảm crit nhận vào)
    {
        "id": "thuy", "ten": "Thủy Linh Căn", "emoji": E_THUY_LINH_CAN,
        "mau": 0x2080D0, "loai": "co_ban",
        "passive": {"hp_flat": 1500, "hp_pct": 4.0, "ho_tam": 300},
        "dot_pha_buff": {"hp_pct": 2.5},
        "chuc_mung": f"{E_THUY_LINH_CAN} Thủy linh căn — sinh lực dồi dào, bất tử chi đạo!",
    },
    # Thổ: chuyên phòng ngự — DEF + kháng bạo, bù thiếu AT
    {
        "id": "tho", "ten": "Thổ Linh Căn", "emoji": E_THO_LINH_CAN,
        "mau": 0xA07820, "loai": "co_ban",
        "passive": {"df_flat": 70, "def_pct": 5.0, "khang_bao": 4.0},
        "dot_pha_buff": {"def_pct": 2.5},
        "chuc_mung": f"{E_THO_LINH_CAN} Thổ linh căn — phòng thủ kiên cố như núi!",
    },
    # Mộc: chuyên farm — drop + EXP + chút HP, không ảnh hưởng combat nhiều
    {
        "id": "moc", "ten": "Mộc Linh Căn", "emoji": E_MOC_LINH_CAN,
        "mau": 0x208040, "loai": "co_ban",
        "passive": {"drop_rate": 15.0, "exp_pct": 10.0, "hp_pct": 2.0},
        "dot_pha_buff": {"drop_rate": 3.0, "exp_pct": 2.0},
        "chuc_mung": f"{E_MOC_LINH_CAN} Mộc linh căn — cơ duyên tự tìm đến!",
    },
    # Kim: cân bằng — không đỉnh điểm ở mặt nào, nhưng ổn định mọi nội dung
    {
        "id": "kim", "ten": "Kim Linh Căn", "emoji": E_KIM_LINH_CAN,
        "mau": 0x909090, "loai": "co_ban",
        "passive": {"at_flat": 20, "df_flat": 40, "at_pct": 2.5, "def_pct": 2.5, "hoi_tam": 80},
        "dot_pha_buff": {"at_pct": 1.0, "def_pct": 1.5},
        "chuc_mung": f"{E_KIM_LINH_CAN} Kim linh căn — cân bằng âm dương, vạn pháp quy nhất!",
    },
    # ── CĂN HIẾM (4 loại — chỉ kiếm qua mảnh drop) ───────────────────────────
    # Lôi: AT + Hội Tâm (tăng crit rate thực sự nhờ công thức mới) — tốt nhưng không broken
    {
        "id": "loi", "ten": "Lôi Linh Căn", "emoji": E_LOI_LINH_CAN,
        "mau": 0x9030C0, "loai": "hiem",
        "passive": {"at_flat": 35, "at_pct": 3.0, "hoi_tam": 400, "bao_kich": 2.0},
        "dot_pha_buff": {"hoi_tam": 100, "bao_kich": 1.5},
        "chuc_mung": f"{E_LOI_LINH_CAN} Lôi linh căn — thiên lôi tụ thân, vạn địch bất xâm!",
    },
    # Phong: DEF + Kháng Bạo + Hộ Tâm — chuyên tanker bí cảnh
    {
        "id": "phong", "ten": "Phong Linh Căn", "emoji": E_PHONG_LINH_CAN,
        "mau": 0x1AA0A0, "loai": "hiem",
        "passive": {"df_flat": 80, "def_pct": 4.0, "khang_bao": 7.0, "ho_tam": 400},
        "dot_pha_buff": {"khang_bao": 2.0, "ho_tam": 100},
        "chuc_mung": f"{E_PHONG_LINH_CAN} Phong linh căn — tốc như thiên phong, địch không thể chạm!",
    },
    # Ám: tập trung sát thương boss — bao_kich cao nhưng không buff AT% flat nhiều
    {
        "id": "am", "ten": "Ám Linh Căn", "emoji": E_AM_LINH_CAN,
        "mau": 0x4848B0, "loai": "hiem",
        "passive": {"bao_kich": 4.0, "hoi_tam": 200, "at_pct": 2.0},
        "dot_pha_buff": {"bao_kich": 2.0, "at_pct": 1.0},
        "chuc_mung": f"{E_AM_LINH_CAN} Ám linh căn — bóng tối che phủ, một đòn tất sát!",
    },
    # Quang: toàn năng — một chút mọi thứ, không đỉnh điểm ở đâu nhưng hiếm
    {
        "id": "quang", "ten": "Quang Linh Căn", "emoji": E_QUANG_LINH_CAN,
        "mau": 0xC0A020, "loai": "hiem",
        "passive": {"at_flat": 20, "hp_flat": 800, "df_flat": 30, "exp_pct": 6.0, "hp_pct": 2.5, "hoi_tam": 150},
        "dot_pha_buff": {"at_pct": 0.8, "hp_pct": 0.8, "def_pct": 0.8},
        "chuc_mung": f"{E_QUANG_LINH_CAN} Quang linh căn — ánh sáng vạn cổ, toàn năng chi thể!",
    },
]

# Lookup nhanh
LINH_CAN_BY_ID: dict[str, dict[str, Any]] = {lc["id"]: lc for lc in LINH_CAN}
# Điểm linh căn yêu cầu để nhận dot_pha_buff (lớp 2) khi đột phá đại cảnh
# Key = canh_gioi MỚI sau đột phá
LINH_CAN_DIEM_YEU_CAU: dict[int, int] = {
    1: 200,   # lên Trúc Cơ
    2: 300,   # lên Kết Tinh
    3: 400,   # lên Kim Đan
    4: 600,   # lên Cụ Linh
    5: 900,   # lên Nguyên Anh
    6: 1300,  # lên Hóa Thần
    7: 1600,  # lên Ngộ Đạo
    8: 2400,  # lên Vũ Hóa
    9: 3000,  # lên Đăng Tiên
}

LINH_CAN_CO_BAN: list[str] = [lc["id"] for lc in LINH_CAN if lc["loai"] == "co_ban"]  # 5 căn cơ bản
LINH_CAN_HIEM: list[str]   = [lc["id"] for lc in LINH_CAN if lc["loai"] == "hiem"]    # 4 căn hiếm

# Yêu cầu điểm linh căn để đột phá cảnh giới LỚN (index = cg_id đích)
# Ví dụ: đột phá lên Trúc Cơ (cg=1) cần 100đ mỗi căn đang sở hữu
LINH_CAN_YEU_CAU_DIEM: list[int] = [0, 200, 300, 400, 600, 900, 1300, 1600, 2400, 3000]

# ══════════════════════════════════════════════════════
#  THỂ CHẤT TU LUYỆN — 10 loại, random khi tạo hồ sơ
#  buff: stat bonus cố định (% và flat)
#  rate: tỉ lệ random (tổng = 100)
# ══════════════════════════════════════════════════════
THE_CHAT: list[dict[str, Any]] = [
    # ── THẦN CẤP (0.2% mỗi loại — vạn cổ cực hiếm) ───────────────────────────
    # Hỗn Độn: toàn diện tuyệt đỉnh — xứng đáng "vạn cổ đệ nhất"
    {
        "id": "hon_don_thanh_the", "ten": "Hỗn Độn Thánh Thể",
        "emoji": "🌌", "mau": 0xF0D060, "rate": 0.2,
        "mo_ta": "Cân bằng tuyệt đối — vạn cổ đệ nhất thể chất",
        "buff": {"at_pct": 22.0, "def_pct": 14.0, "hp_pct": 16.0,
                 "exp_m": 1.5, "lt_m": 1.5,
                 "hoi_tam": 400, "bao_kich": 4.0, "khang_bao": 4.0,
                 "drop_rate": 12.0},
        "chuc_mung": "🌌 Vạn cổ đệ nhất! Hỗn Độn Thánh Thể xuất thế!",
    },
    # Vô Thủy: farm + tu luyện đỉnh, có chút combat utility
    {
        "id": "vo_thuy_tien_the", "ten": "Vô Thủy Tiên Thể",
        "emoji": "💫", "mau": 0x60C0FF, "rate": 0.2,
        "mo_ta": "Tu luyện tốc độ vô song — thiên tài bậc nhất",
        "buff": {"exp_m": 2.5, "lt_m": 2.0, "cd_tu_luyen_pct": -40.0,
                 "hp_pct": 10.0, "at_pct": 12.0,
                 "hoi_tam": 300, "bao_kich": 2.0, "drop_rate": 20.0},
        "chuc_mung": "💫 Vô Thủy Tiên Thể — tu luyện nhanh nhất thiên hạ!",
    },
    # ── THIÊN CẤP (2% mỗi loại — hiếm, chuyên biệt) ──────────────────────────
    # Lôi Ngục: DPS, nhưng bớt AT% để không one-shot, đổi bằng Hội Tâm nhiều hơn
    {
        "id": "loi_nguc_than_the", "ten": "Lôi Ngục Thần Thể",
        "emoji": "⚡", "mau": 0xD060FF, "rate": 2.0,
        "mo_ta": "Bạo kích cực cao — sát thương thiên lôi",
        "buff": {"at_pct": 18.0, "bao_kich": 6.0, "hoi_tam": 500, "hp_pct": -5.0},
        "chuc_mung": "⚡ Lôi Ngục Thần Thể — thiên lôi hóa thân!",
    },
    # Huyền Âm: tank, không có AT nhiều, đổi bằng HP+DEF cực cao
    {
        "id": "huyen_am_ma_the", "ten": "Huyền Âm Ma Thể",
        "emoji": "🛡️", "mau": 0x40E0C0, "rate": 2.0,
        "mo_ta": "Phòng thủ tuyệt đối — hấp thụ sát thương",
        "buff": {"hp_pct": 22.0, "def_pct": 15.0, "khang_bao": 5.0, "ho_tam": 300},
        "chuc_mung": "🛡️ Huyền Âm Ma Thể — bất tử chi thân!",
    },
    # Thái Dương: DPS thuần, bớt so với cũ
    {
        "id": "thai_duong_dao_the", "ten": "Thái Dương Đạo Thể",
        "emoji": "☀️", "mau": 0xFF8030, "rate": 2.0,
        "mo_ta": "Tấn công thuần túy — đốt cháy mọi kẻ địch",
        "buff": {"at_pct": 22.0, "bao_kich": 4.0, "exp_m": 1.2},
        "chuc_mung": "☀️ Thái Dương Đạo Thể — thiêu đốt vạn linh!",
    },
    # ── ĐỊA CẤP (8% mỗi loại — uncommon) ─────────────────────────────────────
    # Cửu Biến Kim: cân bằng, buff vừa phải mọi mặt
    {
        "id": "cuu_bien_kim_the", "ten": "Cửu Biến Kim Thể",
        "emoji": "⚔️", "mau": 0xC0C0C0, "rate": 8.0,
        "mo_ta": "Cân bằng công thủ — ổn định mọi nội dung",
        "buff": {"at_pct": 15.0, "def_pct": 8.0, "hp_pct": 5.0, "hoi_tam": 180, "bao_kich": 3.0},
        "chuc_mung": "⚔️ Cửu Biến Kim Thể — vạn pháp cân bằng!",
    },
    # Thiên Mệnh: farm tốt, combat yếu — rõ vai trò
    {
        "id": "thien_menh_linh_the", "ten": "Thiên Mệnh Linh Thể",
        "emoji": "🍀", "mau": 0x50D050, "rate": 8.0,
        "mo_ta": "May mắn thiên phú — drop và farm tốt nhất",
        "buff": {"drop_rate": 15.0, "lt_m": 1.6, "exp_m": 1.3, "hp_pct": 3.0},
        "chuc_mung": "🍀 Thiên Mệnh Linh Thể — cơ duyên tự tìm đến!",
    },
    # Băng Hỏa: DPS + chút sinh tồn — nằm giữa AT và tank
    {
        "id": "bang_hoa_song_the", "ten": "Băng Hỏa Song Thể",
        "emoji": "🌋", "mau": 0xFF6030, "rate": 8.0,
        "mo_ta": "Lưỡng hệ hiếm — tấn công đa dạng",
        "buff": {"at_pct": 14.0, "hp_pct": 8.0, "bao_kich": 5.0, "hoi_tam": 180},
        "chuc_mung": "🌋 Băng Hỏa Song Thể — lưỡng hệ dị tài!",
    },
    # ── PHÀM CẤP (34.3%/35.3% — phổ thông) ──────────────────────────────────
    {
        "id": "pham_tien_the", "ten": "Phàm Tiên Thể",
        "emoji": "🌱", "mau": 0x8888AA, "rate": 34.3,
        "mo_ta": "Thể chất thường gặp — buff nhỏ đều các mặt",
        "buff": {"at_pct": 6.0, "def_pct": 6.0, "hp_pct": 6.0, "exp_m": 1.1},
        "chuc_mung": "🌱 Phàm Tiên Thể — con đường dài nhưng vững chắc!",
    },
    {
        "id": "tuc_cot_pham_the", "ten": "Tục Cốt Phàm Thể",
        "emoji": "👤", "mau": 0x555555, "rate": 35.3,
        "mo_ta": "Thể chất phổ thông — tuy khó nhọc nhưng ý chí bền vững",
        "buff": {"at_pct": 2.0, "def_pct": 2.0, "hp_pct": 2.0,
                 "exp_m": 1.15, "ho_tam": 120},
        "chuc_mung": "👤 Tục Cốt Phàm Thể — con đường gian nan phía trước!",
    },
]

THE_CHAT_BY_ID: dict[str, dict[str, Any]] = {tc["id"]: tc for tc in THE_CHAT}

# ══════════════════════════════════════════════════════
#  TÔNG MÔN
# ══════════════════════════════════════════════════════
TONG_MON: list[dict[str, Any]] = [
    {"id": 0, "ten": "Ma Giáo",    "emoji": "💀",  "buff": "cong",       "buff_val": 1.5,
     "mo_ta": "Con đường ma đạo — sát thương là tất cả. Tấn công ×1.5."},
    {"id": 1, "ten": "Côn Lôn",   "emoji": "⛰️",  "buff": "linh_thach", "buff_val": 1.4,
     "mo_ta": "Danh môn chính phái — tích lũy linh thạch ×1.4."},
    {"id": 2, "ten": "Phật Giáo", "emoji": "☸️",  "buff": "hp",          "buff_val": 1.5,
     "mo_ta": "Kim cang bất hoại — sinh lực ×1.5."},
]

# ══════════════════════════════════════════════════════
#  THUỘC TÍNH / PHÁP BẢO
# ══════════════════════════════════════════════════════
# ══════════════════════════════════════════════════════════════
#  PHÁP BẢO — BASE CONFIG (chỉnh sửa tại đây)
#  10 loại × 9 cảnh giới = 90 entries
# ══════════════════════════════════════════════════════════════
PHAP_BAO_BASE: list[dict[str, Any]] = [
    # id_base, ten,           emoji,                                            at0, df0, base_passive (CG0),        mo_ta
    {"id_base": 0, "ten": "Hiệu Giác",  "emoji": "<:hieugiac:1482901981314945067>",  "at0": 8,  "df0": 0,  "passive0": {"at_pct": 2.0},                    "mo_ta": "Công kích sắc bén — tấn công tăng"},
    {"id_base": 1, "ten": "Hoàng Cực",  "emoji": "<:hoangcuc:1482901980358639699>",  "at0": 0,  "df0": 12, "passive0": {"df_pct": 2.0},                    "mo_ta": "Phòng ngự vững chắc — phòng thủ tăng"},
    {"id_base": 2, "ten": "Tinh Chùy",  "emoji": "<:tinhchuy:1482901979087769804>",  "at0": 10, "df0": 3,  "passive0": {"at_pct": 2.0},                    "mo_ta": "Vũ khí công thủ — thiên về tấn công"},
    {"id_base": 3, "ten": "Huyền Chung","emoji": "<:huyenchung:1482901978232127499>","at0": 3,  "df0": 10, "passive0": {"hp_pct": 1.0, "df_pct": 2.0},     "mo_ta": "Linh chung hộ thể — thiên về phòng thủ"},
    {"id_base": 4, "ten": "Huyết Diện", "emoji": "<:huyetdien:1482901977586208920>", "at0": 12, "df0": 2,  "passive0": {"at_pct": 3.0},                    "mo_ta": "Diện mạo huyết sát — bạo kích tăng"},
    {"id_base": 5, "ten": "Chi Kỳ",     "emoji": "<:chiky:1482901976457937117>",     "at0": 6,  "df0": 6,  "passive0": {"at_pct": 1.0, "df_pct": 1.0},     "mo_ta": "Cờ trận cân bằng — tăng đều AT/DEF"},
    {"id_base": 6, "ten": "Ngưng Châu", "emoji": "<:ngungchau:1482901974998450247>", "at0": 4,  "df0": 4,  "passive0": {"hp_pct": 2.0},                    "mo_ta": "Châu ngưng linh khí — tăng sinh lực"},
    {"id_base": 7, "ten": "Bạch Bào",   "emoji": "<:bachbao:1482901973366865920>",   "at0": 2,  "df0": 14, "passive0": {"hp_pct": 1.0, "df_pct": 3.0},     "mo_ta": "Áo trắng hộ thể — phòng ngự cao nhất"},
    {"id_base": 8, "ten": "Thiết Bích", "emoji": "<:thietbich:1482901970003169360>", "at0": 8,  "df0": 8,  "passive0": {"hp_pct": 1.0, "at_pct": 1.0, "df_pct": 1.0}, "mo_ta": "Thiết bích kim thành — cân bằng cao cấp"},
    {"id_base": 9, "ten": "Cổ Cầm",     "emoji": "<:cocam:1482901971609325568>",     "at0": 14, "df0": 0,  "passive0": {"at_pct": 3.0},                    "mo_ta": "Cổ cầm linh âm — tấn công cao nhất"},
]

_PB_SCALE = 1.8  # AT/DF nhân thêm ×1.8 mỗi cảnh giới
_PB_PASSIVE_STEP = 0.2  # passive tăng 0.2% mỗi cảnh giới
# Lưu ý: bảng PHAP_BAO bên dưới được hard-code thay vì generate động
# để dễ kiểm soát từng entry khi cần fine-tune balance.

PHAP_BAO: list[dict[str, Any]] = [
    {"id":  0, "id_base":0, "ten":"Hiệu Giác", "emoji":"<:hieugiac:1482901981314945067>", "canh_gioi":0, "at":    8, "df":    0, "passive":{'at_pct': 2.0}, "mo_ta":"Công kích sắc bén — tấn công tăng"},
    {"id":  1, "id_base":0, "ten":"Hiệu Giác", "emoji":"<:hieugiac:1482901981314945067>", "canh_gioi":1, "at":   14, "df":    0, "passive":{'hp_pct': 0.3, 'at_pct': 2.2, 'df_pct': 0.2}, "mo_ta":"Công kích sắc bén — tấn công tăng"},
    {"id":  2, "id_base":0, "ten":"Hiệu Giác", "emoji":"<:hieugiac:1482901981314945067>", "canh_gioi":2, "at":   25, "df":    0, "passive":{'hp_pct': 0.6, 'at_pct': 2.4, 'df_pct': 0.4}, "mo_ta":"Công kích sắc bén — tấn công tăng"},
    {"id":  3, "id_base":0, "ten":"Hiệu Giác", "emoji":"<:hieugiac:1482901981314945067>", "canh_gioi":3, "at":   46, "df":    0, "passive":{'hp_pct': 0.9, 'at_pct': 2.6, 'df_pct': 0.6}, "mo_ta":"Công kích sắc bén — tấn công tăng"},
    {"id":  4, "id_base":0, "ten":"Hiệu Giác", "emoji":"<:hieugiac:1482901981314945067>", "canh_gioi":4, "at":   84, "df":    0, "passive":{'hp_pct': 1.2, 'at_pct': 2.8, 'df_pct': 0.8}, "mo_ta":"Công kích sắc bén — tấn công tăng"},
    {"id":  5, "id_base":0, "ten":"Hiệu Giác", "emoji":"<:hieugiac:1482901981314945067>", "canh_gioi":5, "at":  151, "df":    0, "passive":{'hp_pct': 1.5, 'at_pct': 3.0, 'df_pct': 1.0}, "mo_ta":"Công kích sắc bén — tấn công tăng"},
    {"id":  6, "id_base":0, "ten":"Hiệu Giác", "emoji":"<:hieugiac:1482901981314945067>", "canh_gioi":6, "at":  272, "df":    0, "passive":{'hp_pct': 1.8, 'at_pct': 3.2, 'df_pct': 1.2}, "mo_ta":"Công kích sắc bén — tấn công tăng"},
    {"id":  7, "id_base":0, "ten":"Hiệu Giác", "emoji":"<:hieugiac:1482901981314945067>", "canh_gioi":7, "at":  488, "df":    0, "passive":{'hp_pct': 2.1, 'at_pct': 3.4, 'df_pct': 1.4}, "mo_ta":"Công kích sắc bén — tấn công tăng"},
    {"id":  8, "id_base":0, "ten":"Hiệu Giác", "emoji":"<:hieugiac:1482901981314945067>", "canh_gioi":8, "at":  880, "df":    0, "passive":{'hp_pct': 2.4, 'at_pct': 3.6, 'df_pct': 1.6}, "mo_ta":"Công kích sắc bén — tấn công tăng"},
    {"id":  9, "id_base":1, "ten":"Hoàng Cực", "emoji":"<:hoangcuc:1482901980358639699>", "canh_gioi":0, "at":    0, "df":   12, "passive":{'df_pct': 2.0}, "mo_ta":"Phòng ngự vững chắc — phòng thủ tăng"},
    {"id": 10, "id_base":1, "ten":"Hoàng Cực", "emoji":"<:hoangcuc:1482901980358639699>", "canh_gioi":1, "at":    0, "df":   21, "passive":{'hp_pct': 0.3, 'at_pct': 0.2, 'df_pct': 2.2}, "mo_ta":"Phòng ngự vững chắc — phòng thủ tăng"},
    {"id": 11, "id_base":1, "ten":"Hoàng Cực", "emoji":"<:hoangcuc:1482901980358639699>", "canh_gioi":2, "at":    0, "df":   38, "passive":{'hp_pct': 0.6, 'at_pct': 0.4, 'df_pct': 2.4}, "mo_ta":"Phòng ngự vững chắc — phòng thủ tăng"},
    {"id": 12, "id_base":1, "ten":"Hoàng Cực", "emoji":"<:hoangcuc:1482901980358639699>", "canh_gioi":3, "at":    0, "df":   69, "passive":{'hp_pct': 0.9, 'at_pct': 0.6, 'df_pct': 2.6}, "mo_ta":"Phòng ngự vững chắc — phòng thủ tăng"},
    {"id": 13, "id_base":1, "ten":"Hoàng Cực", "emoji":"<:hoangcuc:1482901980358639699>", "canh_gioi":4, "at":    0, "df":  126, "passive":{'hp_pct': 1.2, 'at_pct': 0.8, 'df_pct': 2.8}, "mo_ta":"Phòng ngự vững chắc — phòng thủ tăng"},
    {"id": 14, "id_base":1, "ten":"Hoàng Cực", "emoji":"<:hoangcuc:1482901980358639699>", "canh_gioi":5, "at":    0, "df":  226, "passive":{'hp_pct': 1.5, 'at_pct': 1.0, 'df_pct': 3.0}, "mo_ta":"Phòng ngự vững chắc — phòng thủ tăng"},
    {"id": 15, "id_base":1, "ten":"Hoàng Cực", "emoji":"<:hoangcuc:1482901980358639699>", "canh_gioi":6, "at":    0, "df":  408, "passive":{'hp_pct': 1.8, 'at_pct': 1.2, 'df_pct': 3.2}, "mo_ta":"Phòng ngự vững chắc — phòng thủ tăng"},
    {"id": 16, "id_base":1, "ten":"Hoàng Cực", "emoji":"<:hoangcuc:1482901980358639699>", "canh_gioi":7, "at":    0, "df":  732, "passive":{'hp_pct': 2.1, 'at_pct': 1.4, 'df_pct': 3.4}, "mo_ta":"Phòng ngự vững chắc — phòng thủ tăng"},
    {"id": 17, "id_base":1, "ten":"Hoàng Cực", "emoji":"<:hoangcuc:1482901980358639699>", "canh_gioi":8, "at":    0, "df": 1320, "passive":{'hp_pct': 2.4, 'at_pct': 1.6, 'df_pct': 3.6}, "mo_ta":"Phòng ngự vững chắc — phòng thủ tăng"},
    {"id": 18, "id_base":2, "ten":"Tinh Chùy", "emoji":"<:tinhchuy:1482901979087769804>", "canh_gioi":0, "at":   10, "df":    3, "passive":{'at_pct': 2.0}, "mo_ta":"Vũ khí công thủ — thiên về tấn công"},
    {"id": 19, "id_base":2, "ten":"Tinh Chùy", "emoji":"<:tinhchuy:1482901979087769804>", "canh_gioi":1, "at":   18, "df":    5, "passive":{'hp_pct': 0.3, 'at_pct': 2.2, 'df_pct': 0.2}, "mo_ta":"Vũ khí công thủ — thiên về tấn công"},
    {"id": 20, "id_base":2, "ten":"Tinh Chùy", "emoji":"<:tinhchuy:1482901979087769804>", "canh_gioi":2, "at":   32, "df":    9, "passive":{'hp_pct': 0.6, 'at_pct': 2.4, 'df_pct': 0.4}, "mo_ta":"Vũ khí công thủ — thiên về tấn công"},
    {"id": 21, "id_base":2, "ten":"Tinh Chùy", "emoji":"<:tinhchuy:1482901979087769804>", "canh_gioi":3, "at":   58, "df":   17, "passive":{'hp_pct': 0.9, 'at_pct': 2.6, 'df_pct': 0.6}, "mo_ta":"Vũ khí công thủ — thiên về tấn công"},
    {"id": 22, "id_base":2, "ten":"Tinh Chùy", "emoji":"<:tinhchuy:1482901979087769804>", "canh_gioi":4, "at":  105, "df":   31, "passive":{'hp_pct': 1.2, 'at_pct': 2.8, 'df_pct': 0.8}, "mo_ta":"Vũ khí công thủ — thiên về tấn công"},
    {"id": 23, "id_base":2, "ten":"Tinh Chùy", "emoji":"<:tinhchuy:1482901979087769804>", "canh_gioi":5, "at":  189, "df":   56, "passive":{'hp_pct': 1.5, 'at_pct': 3.0, 'df_pct': 1.0}, "mo_ta":"Vũ khí công thủ — thiên về tấn công"},
    {"id": 24, "id_base":2, "ten":"Tinh Chùy", "emoji":"<:tinhchuy:1482901979087769804>", "canh_gioi":6, "at":  340, "df":  102, "passive":{'hp_pct': 1.8, 'at_pct': 3.2, 'df_pct': 1.2}, "mo_ta":"Vũ khí công thủ — thiên về tấn công"},
    {"id": 25, "id_base":2, "ten":"Tinh Chùy", "emoji":"<:tinhchuy:1482901979087769804>", "canh_gioi":7, "at":  610, "df":  183, "passive":{'hp_pct': 2.1, 'at_pct': 3.4, 'df_pct': 1.4}, "mo_ta":"Vũ khí công thủ — thiên về tấn công"},
    {"id": 26, "id_base":2, "ten":"Tinh Chùy", "emoji":"<:tinhchuy:1482901979087769804>", "canh_gioi":8, "at": 1100, "df":  330, "passive":{'hp_pct': 2.4, 'at_pct': 3.6, 'df_pct': 1.6}, "mo_ta":"Vũ khí công thủ — thiên về tấn công"},
    {"id": 27, "id_base":3, "ten":"Huyền Chung", "emoji":"<:huyenchung:1482901978232127499>", "canh_gioi":0, "at":    3, "df":   10, "passive":{'hp_pct': 1.0, 'df_pct': 2.0}, "mo_ta":"Linh chung hộ thể — thiên về phòng thủ"},
    {"id": 28, "id_base":3, "ten":"Huyền Chung", "emoji":"<:huyenchung:1482901978232127499>", "canh_gioi":1, "at":    5, "df":   18, "passive":{'hp_pct': 1.3, 'at_pct': 0.2, 'df_pct': 2.2}, "mo_ta":"Linh chung hộ thể — thiên về phòng thủ"},
    {"id": 29, "id_base":3, "ten":"Huyền Chung", "emoji":"<:huyenchung:1482901978232127499>", "canh_gioi":2, "at":    9, "df":   32, "passive":{'hp_pct': 1.6, 'at_pct': 0.4, 'df_pct': 2.4}, "mo_ta":"Linh chung hộ thể — thiên về phòng thủ"},
    {"id": 30, "id_base":3, "ten":"Huyền Chung", "emoji":"<:huyenchung:1482901978232127499>", "canh_gioi":3, "at":   17, "df":   58, "passive":{'hp_pct': 1.9, 'at_pct': 0.6, 'df_pct': 2.6}, "mo_ta":"Linh chung hộ thể — thiên về phòng thủ"},
    {"id": 31, "id_base":3, "ten":"Huyền Chung", "emoji":"<:huyenchung:1482901978232127499>", "canh_gioi":4, "at":   31, "df":  105, "passive":{'hp_pct': 2.2, 'at_pct': 0.8, 'df_pct': 2.8}, "mo_ta":"Linh chung hộ thể — thiên về phòng thủ"},
    {"id": 32, "id_base":3, "ten":"Huyền Chung", "emoji":"<:huyenchung:1482901978232127499>", "canh_gioi":5, "at":   56, "df":  189, "passive":{'hp_pct': 2.5, 'at_pct': 1.0, 'df_pct': 3.0}, "mo_ta":"Linh chung hộ thể — thiên về phòng thủ"},
    {"id": 33, "id_base":3, "ten":"Huyền Chung", "emoji":"<:huyenchung:1482901978232127499>", "canh_gioi":6, "at":  102, "df":  340, "passive":{'hp_pct': 2.8, 'at_pct': 1.2, 'df_pct': 3.2}, "mo_ta":"Linh chung hộ thể — thiên về phòng thủ"},
    {"id": 34, "id_base":3, "ten":"Huyền Chung", "emoji":"<:huyenchung:1482901978232127499>", "canh_gioi":7, "at":  183, "df":  610, "passive":{'hp_pct': 3.1, 'at_pct': 1.4, 'df_pct': 3.4}, "mo_ta":"Linh chung hộ thể — thiên về phòng thủ"},
    {"id": 35, "id_base":3, "ten":"Huyền Chung", "emoji":"<:huyenchung:1482901978232127499>", "canh_gioi":8, "at":  330, "df": 1100, "passive":{'hp_pct': 3.4, 'at_pct': 1.6, 'df_pct': 3.6}, "mo_ta":"Linh chung hộ thể — thiên về phòng thủ"},
    {"id": 36, "id_base":4, "ten":"Huyết Diện", "emoji":"<:huyetdien:1482901977586208920>", "canh_gioi":0, "at":   12, "df":    2, "passive":{'at_pct': 3.0}, "mo_ta":"Diện mạo huyết sát — bạo kích tăng"},
    {"id": 37, "id_base":4, "ten":"Huyết Diện", "emoji":"<:huyetdien:1482901977586208920>", "canh_gioi":1, "at":   21, "df":    3, "passive":{'hp_pct': 0.3, 'at_pct': 3.2, 'df_pct': 0.2}, "mo_ta":"Diện mạo huyết sát — bạo kích tăng"},
    {"id": 38, "id_base":4, "ten":"Huyết Diện", "emoji":"<:huyetdien:1482901977586208920>", "canh_gioi":2, "at":   38, "df":    6, "passive":{'hp_pct': 0.6, 'at_pct': 3.4, 'df_pct': 0.4}, "mo_ta":"Diện mạo huyết sát — bạo kích tăng"},
    {"id": 39, "id_base":4, "ten":"Huyết Diện", "emoji":"<:huyetdien:1482901977586208920>", "canh_gioi":3, "at":   69, "df":   11, "passive":{'hp_pct': 0.9, 'at_pct': 3.6, 'df_pct': 0.6}, "mo_ta":"Diện mạo huyết sát — bạo kích tăng"},
    {"id": 40, "id_base":4, "ten":"Huyết Diện", "emoji":"<:huyetdien:1482901977586208920>", "canh_gioi":4, "at":  126, "df":   21, "passive":{'hp_pct': 1.2, 'at_pct': 3.8, 'df_pct': 0.8}, "mo_ta":"Diện mạo huyết sát — bạo kích tăng"},
    {"id": 41, "id_base":4, "ten":"Huyết Diện", "emoji":"<:huyetdien:1482901977586208920>", "canh_gioi":5, "at":  226, "df":   37, "passive":{'hp_pct': 1.5, 'at_pct': 4.0, 'df_pct': 1.0}, "mo_ta":"Diện mạo huyết sát — bạo kích tăng"},
    {"id": 42, "id_base":4, "ten":"Huyết Diện", "emoji":"<:huyetdien:1482901977586208920>", "canh_gioi":6, "at":  408, "df":   68, "passive":{'hp_pct': 1.8, 'at_pct': 4.2, 'df_pct': 1.2}, "mo_ta":"Diện mạo huyết sát — bạo kích tăng"},
    {"id": 43, "id_base":4, "ten":"Huyết Diện", "emoji":"<:huyetdien:1482901977586208920>", "canh_gioi":7, "at":  732, "df":  122, "passive":{'hp_pct': 2.1, 'at_pct': 4.4, 'df_pct': 1.4}, "mo_ta":"Diện mạo huyết sát — bạo kích tăng"},
    {"id": 44, "id_base":4, "ten":"Huyết Diện", "emoji":"<:huyetdien:1482901977586208920>", "canh_gioi":8, "at": 1320, "df":  220, "passive":{'hp_pct': 2.4, 'at_pct': 4.6, 'df_pct': 1.6}, "mo_ta":"Diện mạo huyết sát — bạo kích tăng"},
    {"id": 45, "id_base":5, "ten":"Chi Kỳ", "emoji":"<:chiky:1482901976457937117>", "canh_gioi":0, "at":    6, "df":    6, "passive":{'at_pct': 1.0, 'df_pct': 1.0}, "mo_ta":"Cờ trận cân bằng — tăng đều AT/DEF"},
    {"id": 46, "id_base":5, "ten":"Chi Kỳ", "emoji":"<:chiky:1482901976457937117>", "canh_gioi":1, "at":   10, "df":   10, "passive":{'hp_pct': 0.3, 'at_pct': 1.2, 'df_pct': 1.2}, "mo_ta":"Cờ trận cân bằng — tăng đều AT/DEF"},
    {"id": 47, "id_base":5, "ten":"Chi Kỳ", "emoji":"<:chiky:1482901976457937117>", "canh_gioi":2, "at":   19, "df":   19, "passive":{'hp_pct': 0.6, 'at_pct': 1.4, 'df_pct': 1.4}, "mo_ta":"Cờ trận cân bằng — tăng đều AT/DEF"},
    {"id": 48, "id_base":5, "ten":"Chi Kỳ", "emoji":"<:chiky:1482901976457937117>", "canh_gioi":3, "at":   34, "df":   34, "passive":{'hp_pct': 0.9, 'at_pct': 1.6, 'df_pct': 1.6}, "mo_ta":"Cờ trận cân bằng — tăng đều AT/DEF"},
    {"id": 49, "id_base":5, "ten":"Chi Kỳ", "emoji":"<:chiky:1482901976457937117>", "canh_gioi":4, "at":   63, "df":   63, "passive":{'hp_pct': 1.2, 'at_pct': 1.8, 'df_pct': 1.8}, "mo_ta":"Cờ trận cân bằng — tăng đều AT/DEF"},
    {"id": 50, "id_base":5, "ten":"Chi Kỳ", "emoji":"<:chiky:1482901976457937117>", "canh_gioi":5, "at":  113, "df":  113, "passive":{'hp_pct': 1.5, 'at_pct': 2.0, 'df_pct': 2.0}, "mo_ta":"Cờ trận cân bằng — tăng đều AT/DEF"},
    {"id": 51, "id_base":5, "ten":"Chi Kỳ", "emoji":"<:chiky:1482901976457937117>", "canh_gioi":6, "at":  204, "df":  204, "passive":{'hp_pct': 1.8, 'at_pct': 2.2, 'df_pct': 2.2}, "mo_ta":"Cờ trận cân bằng — tăng đều AT/DEF"},
    {"id": 52, "id_base":5, "ten":"Chi Kỳ", "emoji":"<:chiky:1482901976457937117>", "canh_gioi":7, "at":  366, "df":  366, "passive":{'hp_pct': 2.1, 'at_pct': 2.4, 'df_pct': 2.4}, "mo_ta":"Cờ trận cân bằng — tăng đều AT/DEF"},
    {"id": 53, "id_base":5, "ten":"Chi Kỳ", "emoji":"<:chiky:1482901976457937117>", "canh_gioi":8, "at":  660, "df":  660, "passive":{'hp_pct': 2.4, 'at_pct': 2.6, 'df_pct': 2.6}, "mo_ta":"Cờ trận cân bằng — tăng đều AT/DEF"},
    {"id": 54, "id_base":6, "ten":"Ngưng Châu", "emoji":"<:ngungchau:1482901974998450247>", "canh_gioi":0, "at":    4, "df":    4, "passive":{'hp_pct': 2.0}, "mo_ta":"Châu ngưng linh khí — tăng sinh lực"},
    {"id": 55, "id_base":6, "ten":"Ngưng Châu", "emoji":"<:ngungchau:1482901974998450247>", "canh_gioi":1, "at":    7, "df":    7, "passive":{'hp_pct': 2.3, 'at_pct': 0.2, 'df_pct': 0.2}, "mo_ta":"Châu ngưng linh khí — tăng sinh lực"},
    {"id": 56, "id_base":6, "ten":"Ngưng Châu", "emoji":"<:ngungchau:1482901974998450247>", "canh_gioi":2, "at":   12, "df":   12, "passive":{'hp_pct': 2.6, 'at_pct': 0.4, 'df_pct': 0.4}, "mo_ta":"Châu ngưng linh khí — tăng sinh lực"},
    {"id": 57, "id_base":6, "ten":"Ngưng Châu", "emoji":"<:ngungchau:1482901974998450247>", "canh_gioi":3, "at":   23, "df":   23, "passive":{'hp_pct': 2.9, 'at_pct': 0.6, 'df_pct': 0.6}, "mo_ta":"Châu ngưng linh khí — tăng sinh lực"},
    {"id": 58, "id_base":6, "ten":"Ngưng Châu", "emoji":"<:ngungchau:1482901974998450247>", "canh_gioi":4, "at":   42, "df":   42, "passive":{'hp_pct': 3.2, 'at_pct': 0.8, 'df_pct': 0.8}, "mo_ta":"Châu ngưng linh khí — tăng sinh lực"},
    {"id": 59, "id_base":6, "ten":"Ngưng Châu", "emoji":"<:ngungchau:1482901974998450247>", "canh_gioi":5, "at":   75, "df":   75, "passive":{'hp_pct': 3.5, 'at_pct': 1.0, 'df_pct': 1.0}, "mo_ta":"Châu ngưng linh khí — tăng sinh lực"},
    {"id": 60, "id_base":6, "ten":"Ngưng Châu", "emoji":"<:ngungchau:1482901974998450247>", "canh_gioi":6, "at":  136, "df":  136, "passive":{'hp_pct': 3.8, 'at_pct': 1.2, 'df_pct': 1.2}, "mo_ta":"Châu ngưng linh khí — tăng sinh lực"},
    {"id": 61, "id_base":6, "ten":"Ngưng Châu", "emoji":"<:ngungchau:1482901974998450247>", "canh_gioi":7, "at":  244, "df":  244, "passive":{'hp_pct': 4.1, 'at_pct': 1.4, 'df_pct': 1.4}, "mo_ta":"Châu ngưng linh khí — tăng sinh力"},
    {"id": 62, "id_base":6, "ten":"Ngưng Châu", "emoji":"<:ngungchau:1482901974998450247>", "canh_gioi":8, "at":  440, "df":  440, "passive":{'hp_pct': 4.4, 'at_pct': 1.6, 'df_pct': 1.6}, "mo_ta":"Châu ngưng linh khí — tăng sinh力"},
    {"id": 63, "id_base":7, "ten":"Bạch Bào", "emoji":"<:bachbao:1482901973366865920>", "canh_gioi":0, "at":    2, "df":   14, "passive":{'hp_pct': 1.0, 'df_pct': 3.0}, "mo_ta":"Áo trắng hộ thể — phòng ngự cao nhất"},
    {"id": 64, "id_base":7, "ten":"Bạch Bào", "emoji":"<:bachbao:1482901973366865920>", "canh_gioi":1, "at":    3, "df":   25, "passive":{'hp_pct': 1.3, 'at_pct': 0.2, 'df_pct': 3.2}, "mo_ta":"Áo trắng hộ thể — phòng ngự cao nhất"},
    {"id": 65, "id_base":7, "ten":"Bạch Bào", "emoji":"<:bachbao:1482901973366865920>", "canh_gioi":2, "at":    6, "df":   44, "passive":{'hp_pct': 1.6, 'at_pct': 0.4, 'df_pct': 3.4}, "mo_ta":"Áo trắng hộ thể — phòng ngự cao nhất"},
    {"id": 66, "id_base":7, "ten":"Bạch Bào", "emoji":"<:bachbao:1482901973366865920>", "canh_gioi":3, "at":   11, "df":   81, "passive":{'hp_pct': 1.9, 'at_pct': 0.6, 'df_pct': 3.6}, "mo_ta":"Áo trắng hộ thể — phòng ngự cao nhất"},
    {"id": 67, "id_base":7, "ten":"Bạch Bào", "emoji":"<:bachbao:1482901973366865920>", "canh_gioi":4, "at":   21, "df":  147, "passive":{'hp_pct': 2.2, 'at_pct': 0.8, 'df_pct': 3.8}, "mo_ta":"Áo trắng hộ thể — phòng ngự cao nhất"},
    {"id": 68, "id_base":7, "ten":"Bạch Bào", "emoji":"<:bachbao:1482901973366865920>", "canh_gioi":5, "at":   37, "df":  264, "passive":{'hp_pct': 2.5, 'at_pct': 1.0, 'df_pct': 4.0}, "mo_ta":"Áo trắng hộ thể — phòng ngự cao nhất"},
    {"id": 69, "id_base":7, "ten":"Bạch Bào", "emoji":"<:bachbao:1482901973366865920>", "canh_gioi":6, "at":   68, "df":  476, "passive":{'hp_pct': 2.8, 'at_pct': 1.2, 'df_pct': 4.2}, "mo_ta":"Áo trắng hộ thể — phòng ngự cao nhất"},
    {"id": 70, "id_base":7, "ten":"Bạch Bào", "emoji":"<:bachbao:1482901973366865920>", "canh_gioi":7, "at":  122, "df":  854, "passive":{'hp_pct': 3.1, 'at_pct': 1.4, 'df_pct': 4.4}, "mo_ta":"Áo trắng hộ thể — phòng ngự cao nhất"},
    {"id": 71, "id_base":7, "ten":"Bạch Bào", "emoji":"<:bachbao:1482901973366865920>", "canh_gioi":8, "at":  220, "df": 1540, "passive":{'hp_pct': 3.4, 'at_pct': 1.6, 'df_pct': 4.6}, "mo_ta":"Áo trắng hộ thể — phòng ngự cao nhất"},
    {"id": 72, "id_base":8, "ten":"Thiết Bích", "emoji":"<:thietbich:1482901970003169360>", "canh_gioi":0, "at":    8, "df":    8, "passive":{'hp_pct': 1.0, 'at_pct': 1.0, 'df_pct': 1.0}, "mo_ta":"Thiết bích kim thành — cân bằng cao cấp"},
    {"id": 73, "id_base":8, "ten":"Thiết Bích", "emoji":"<:thietbich:1482901970003169360>", "canh_gioi":1, "at":   14, "df":   14, "passive":{'hp_pct': 1.3, 'at_pct': 1.2, 'df_pct': 1.2}, "mo_ta":"Thiết bích kim thành — cân bằng cao cấp"},
    {"id": 74, "id_base":8, "ten":"Thiết Bích", "emoji":"<:thietbich:1482901970003169360>", "canh_gioi":2, "at":   25, "df":   25, "passive":{'hp_pct': 1.6, 'at_pct': 1.4, 'df_pct': 1.4}, "mo_ta":"Thiết bích kim thành — cân bằng cao cấp"},
    {"id": 75, "id_base":8, "ten":"Thiết Bích", "emoji":"<:thietbich:1482901970003169360>", "canh_gioi":3, "at":   46, "df":   46, "passive":{'hp_pct': 1.9, 'at_pct': 1.6, 'df_pct': 1.6}, "mo_ta":"Thiết bích kim thành — cân bằng cao cấp"},
    {"id": 76, "id_base":8, "ten":"Thiết Bích", "emoji":"<:thietbich:1482901970003169360>", "canh_gioi":4, "at":   84, "df":   84, "passive":{'hp_pct': 2.2, 'at_pct': 1.8, 'df_pct': 1.8}, "mo_ta":"Thiết bích kim thành — cân bằng cao cấp"},
    {"id": 77, "id_base":8, "ten":"Thiết Bích", "emoji":"<:thietbich:1482901970003169360>", "canh_gioi":5, "at":  151, "df":  151, "passive":{'hp_pct': 2.5, 'at_pct': 2.0, 'df_pct': 2.0}, "mo_ta":"Thiết bích kim thành — cân bằng cao cấp"},
    {"id": 78, "id_base":8, "ten":"Thiết Bích", "emoji":"<:thietbich:1482901970003169360>", "canh_gioi":6, "at":  272, "df":  272, "passive":{'hp_pct': 2.8, 'at_pct': 2.2, 'df_pct': 2.2}, "mo_ta":"Thiết bích kim thành — cân bằng cao cấp"},
    {"id": 79, "id_base":8, "ten":"Thiết Bích", "emoji":"<:thietbich:1482901970003169360>", "canh_gioi":7, "at":  488, "df":  488, "passive":{'hp_pct': 3.1, 'at_pct': 2.4, 'df_pct': 2.4}, "mo_ta":"Thiết bích kim thành — cân bằng cao cấp"},
    {"id": 80, "id_base":8, "ten":"Thiết Bích", "emoji":"<:thietbich:1482901970003169360>", "canh_gioi":8, "at":  880, "df":  880, "passive":{'hp_pct': 3.4, 'at_pct': 2.6, 'df_pct': 2.6}, "mo_ta":"Thiết bích kim thành — cân bằng cao cấp"},
    {"id": 81, "id_base":9, "ten":"Cổ Cầm", "emoji":"<:cocam:1482901971609325568>", "canh_gioi":0, "at":   14, "df":    0, "passive":{'at_pct': 3.0}, "mo_ta":"Cổ cầm linh âm — tấn công cao nhất"},
    {"id": 82, "id_base":9, "ten":"Cổ Cầm", "emoji":"<:cocam:1482901971609325568>", "canh_gioi":1, "at":   25, "df":    0, "passive":{'hp_pct': 0.3, 'at_pct': 3.2, 'df_pct': 0.2}, "mo_ta":"Cổ cầm linh âm — tấn công cao nhất"},
    {"id": 83, "id_base":9, "ten":"Cổ Cầm", "emoji":"<:cocam:1482901971609325568>", "canh_gioi":2, "at":   44, "df":    0, "passive":{'hp_pct': 0.6, 'at_pct': 3.4, 'df_pct': 0.4}, "mo_ta":"Cổ cầm linh âm — tấn công cao nhất"},
    {"id": 84, "id_base":9, "ten":"Cổ Cầm", "emoji":"<:cocam:1482901971609325568>", "canh_gioi":3, "at":   81, "df":    0, "passive":{'hp_pct': 0.9, 'at_pct': 3.6, 'df_pct': 0.6}, "mo_ta":"Cổ cầm linh âm — tấn công cao nhất"},
    {"id": 85, "id_base":9, "ten":"Cổ Cầm", "emoji":"<:cocam:1482901971609325568>", "canh_gioi":4, "at":  147, "df":    0, "passive":{'hp_pct': 1.2, 'at_pct': 3.8, 'df_pct': 0.8}, "mo_ta":"Cổ cầm linh âm — tấn công cao nhất"},
    {"id": 86, "id_base":9, "ten":"Cổ Cầm", "emoji":"<:cocam:1482901971609325568>", "canh_gioi":5, "at":  264, "df":    0, "passive":{'hp_pct': 1.5, 'at_pct': 4.0, 'df_pct': 1.0}, "mo_ta":"Cổ cầm linh âm — tấn công cao nhất"},
    {"id": 87, "id_base":9, "ten":"Cổ Cầm", "emoji":"<:cocam:1482901971609325568>", "canh_gioi":6, "at":  476, "df":    0, "passive":{'hp_pct': 1.8, 'at_pct': 4.2, 'df_pct': 1.2}, "mo_ta":"Cổ cầm linh âm — tấn công cao nhất"},
    {"id": 88, "id_base":9, "ten":"Cổ Cầm", "emoji":"<:cocam:1482901971609325568>", "canh_gioi":7, "at":  854, "df":    0, "passive":{'hp_pct': 2.1, 'at_pct': 4.4, 'df_pct': 1.4}, "mo_ta":"Cổ cầm linh âm — tấn công cao nhất"},
    {"id": 89, "id_base":9, "ten":"Cổ Cầm", "emoji":"<:cocam:1482901971609325568>", "canh_gioi":8, "at": 1540, "df":    0, "passive":{'hp_pct': 2.4, 'at_pct': 4.6, 'df_pct': 1.6}, "mo_ta":"Cổ cầm linh âm — tấn công cao nhất"},
]
PHAP_BAO_BY_ID: dict[int, dict[str, Any]] = {pb["id"]: pb for pb in PHAP_BAO}

#  PHÁP BẢO KỸ NĂNG (passive trigger trong bi_canh combat)
# ══════════════════════════════════════════════════════
PHAP_BAO_BY_BASE: dict[int, list[dict[str, Any]]] = {}  # {id_base: [pb_cg0, pb_cg1, ...]  }
for _pb in PHAP_BAO:
    PHAP_BAO_BY_BASE.setdefault(_pb["id_base"], []).append(_pb)
PHAP_BAO_DROP_RATE = 0.02  # 2% từ world boss

# ══════════════════════════════════════════════════════
#  TÀI NGUYÊN / ĐAN DƯỢC
# ══════════════════════════════════════════════════════
DAN_DUOC: list[dict[str, Any]] = [
    {"id": 0, "ten": "Trúc Cơ Đan",       "emoji": E_DAN_TRUC_CO,       "exp": 0, "gia": 2000,   "cap_max": 99, "dot_pha": True, "cg_yeu_cau": 0, "cg_sau": 1, "mo_ta": "Luyện Khí → Trúc Cơ", "shop": False},
    {"id": 1, "ten": "Ngưng Tinh Đan",     "emoji": E_KETTHAN,           "exp": 0, "gia": 5000,   "cap_max": 99, "dot_pha": True, "cg_yeu_cau": 1, "cg_sau": 2, "mo_ta": "Trúc Cơ → Kết Tinh", "shop": False},
    {"id": 2, "ten": "Phá Cảnh Đan",       "emoji": E_DAN_KIM_DAN,       "exp": 0, "gia": 10000,  "cap_max": 99, "dot_pha": True, "cg_yeu_cau": 2, "cg_sau": 3, "mo_ta": "Kết Tinh → Kim Đan", "shop": False},
    {"id": 3, "ten": "Hóa Linh Đan",       "emoji": E_DAN_CU_LINH,       "exp": 0, "gia": 25000,  "cap_max": 99, "dot_pha": True, "cg_yeu_cau": 3, "cg_sau": 4, "mo_ta": "Kim Đan → Cụ Linh", "shop": False},
    {"id": 4, "ten": "Thiên Đạo Chi Khí",  "emoji": E_DAN_NGUYEN_ANH,    "exp": 0, "gia": 50000,  "cap_max": 99, "dot_pha": True, "cg_yeu_cau": 4, "cg_sau": 5, "mo_ta": "Cụ Linh → Nguyên Anh", "shop": False},
    {"id": 5, "ten": "Hóa Thần Chi Khí",   "emoji": E_DAN_HOA_THAN,      "exp": 0, "gia": 100000, "cap_max": 99, "dot_pha": True, "cg_yeu_cau": 5, "cg_sau": 6, "mo_ta": "Nguyên Anh → Hóa Thần", "shop": False},
    {"id": 6, "ten": "Ngộ Đạo Đan",        "emoji": E_DAN_NGO_DAO,       "exp": 0, "gia": 200000, "cap_max": 99, "dot_pha": True, "cg_yeu_cau": 6, "cg_sau": 7, "mo_ta": "Hóa Thần → Ngộ Đạo", "shop": False},
    {"id": 7, "ten": "Vũ Hóa Chi Khí",     "emoji": E_DAN_VU_HOA,        "exp": 0, "gia": 350000, "cap_max": 99, "dot_pha": True, "cg_yeu_cau": 7, "cg_sau": 8, "mo_ta": "Ngộ Đạo → Vũ Hóa", "shop": False},
    {"id": 8, "ten": "Thái Sơ Tiên Lỵ",    "emoji": E_DAN_DANG_TIEN,     "exp": 0, "gia": 500000,  "cap_max": 99, "dot_pha": True, "cg_yeu_cau": 8, "cg_sau": 9, "mo_ta": "Vũ Hóa → Đăng Tiên", "shop": False},
    {"id": 9, "ten": "Tiên Thiên Nhất Khí - Sinh", "emoji": E_TIENTHIENNHATKHI_HIEM, "exp": 0, "gia": 1000000, "cap_max": 99, "dot_pha": True, "cg_yeu_cau": 9, "cap_nho_yeu_cau": 2, "cap_nho_sau": 3, "cg_sau": 9, "mo_ta": "Đăng Tiên Trung Kì → Hậu Kì", "shop": False},
]

NGUYEN_LIEU: list[dict[str, Any]] = [
    {"id": 0, "ten": "Linh Thảo",      "emoji": "🌿", "gia": 10},
    {"id": 1, "ten": "Hỏa Tinh Thạch", "emoji": "🔥", "gia": 50},
    {"id": 2, "ten": "Huyền Thiết",    "emoji": "⚫", "gia": 100},
    {"id": 3, "ten": "Thiên Tằm Tơ",   "emoji": "🕸️", "gia": 200},
    {"id": 4, "ten": "Long Cốt",        "emoji": "🦴", "gia": 500},
    {"id": 5, "ten": "Thần Tinh Sa",    "emoji": "✨", "gia": 2000},
]

# ══════════════════════════════════════════════════════
#  LINH QUẢ — Tăng điểm linh căn
# ══════════════════════════════════════════════════════
LINH_QUA: list[dict[str, Any]] = [
    {"id": "hoa",   "ten": "Hỏa Linh Quả",  "emoji": E_QUA_HOA,   "loai": "co_ban", "diem": 3, "gia": 500,  "mo_ta": "Tăng điểm Hỏa Linh Căn"},
    {"id": "thuy",  "ten": "Thủy Linh Quả", "emoji": E_QUA_THUY,  "loai": "co_ban", "diem": 3, "gia": 500,  "mo_ta": "Tăng điểm Thủy Linh Căn"},
    {"id": "tho",   "ten": "Thổ Linh Quả",  "emoji": E_QUA_THO,   "loai": "co_ban", "diem": 3, "gia": 500,  "mo_ta": "Tăng điểm Thổ Linh Căn"},
    {"id": "moc",   "ten": "Mộc Linh Quả",  "emoji": E_QUA_MOC,   "loai": "co_ban", "diem": 3, "gia": 500,  "mo_ta": "Tăng điểm Mộc Linh Căn"},
    {"id": "kim",   "ten": "Kim Linh Quả",   "emoji": E_QUA_KIM,   "loai": "co_ban", "diem": 3, "gia": 500,  "mo_ta": "Tăng điểm Kim Linh Căn"},
    {"id": "loi",   "ten": "Lôi Linh Quả",   "emoji": E_QUA_LOI,   "loai": "hiem",   "diem": 3, "gia": 3000, "mo_ta": "Tăng điểm Lôi Linh Căn — Hiếm"},
    {"id": "phong", "ten": "Phong Linh Quả", "emoji": E_QUA_PHONG, "loai": "hiem",   "diem": 3, "gia": 3000, "mo_ta": "Tăng điểm Phong Linh Căn — Hiếm"},
    {"id": "am",    "ten": "Ám Linh Quả",    "emoji": E_QUA_AM,    "loai": "hiem",   "diem": 3, "gia": 5000, "mo_ta": "Tăng điểm Ám Linh Căn — Siêu Hiếm"},
    {"id": "quang", "ten": "Quang Linh Quả", "emoji": E_QUA_QUANG, "loai": "hiem",   "diem": 3, "gia": 5000, "mo_ta": "Tăng điểm Quang Linh Căn — Siêu Hiếm"},
]

LINH_QUA_BY_ID: dict[str, dict[str, Any]] = {lq["id"]: lq for lq in LINH_QUA}

LINH_QUA_DROP_CO_BAN = 0.018   # giảm 50%
LINH_QUA_DROP_HIEM   = 0.0045  # giảm 50%
LINH_QUA_DROP_SIEU   = 0.0009  # giảm 50%

# Drop table linh quả theo bc_id: (rate_co_ban, count_per_drop)
# Căn hiếm (loi/phong) × 0.4, siêu hiếm (am/quang) × 0.15
# Drop table linh quả — giảm rate ở BC thấp để cân với thời gian combat dài hơn
# Boss phòng cuối luôn × 1.5 rate
LINH_QUA_BC_DROP: dict[int, tuple[float, int]] = {
    0: (0.03,  1),  # Thạch Thất     — ~15 quả / ~150 run
    1: (0.054, 1),  # Quỷ Cốc        — ~27 quả / ~150 run
    2: (0.09,  1),  # Vạn Sơn        — ~45 quả / ~150 run
    3: (0.144, 1),  # Kiếm Trì       — ~72 quả / ~150 run
    4: (0.30,  1),  # U Uẩn Cốc      — ~105 quả / ~100 run
    5: (0.408, 1),  # Vô Cực         — ~141 quả / ~100 run
    6: (0.528, 1),  # Minh Chủng     — ~186 quả / ~100 run
    7: (0.57,  2),  # Bích Văn       — ~246 quả / ~60 run
    8: (0.528, 3),  # Hư Vô          — ~333 quả / ~60 run
    9: (0.528, 3),  # Tháp Thực Hồn  — ~333 quả / ~60 run
}

MANH_LINH_CAN_EMOJI: dict[str, str] = {
    "hoa":   E_MANH_HOA,   "thuy":  E_MANH_THUY,  "tho":   E_MANH_THO,
    "moc":   E_MANH_MOC,   "kim":   E_MANH_KIM,   "loi":   E_MANH_LOI,
    "phong": E_MANH_PHONG, "am":    E_MANH_AM,    "quang": E_MANH_QUANG,
}

# Giá bán lại shop cho mảnh linh căn (LT)
# Căn cơ bản: 200 LT/mảnh, căn hiếm: 500, siêu hiếm: 1000
MANH_LINH_CAN_GIA: dict[str, int] = {
    "hoa": 200, "thuy": 200, "tho": 200, "moc": 200, "kim": 200,
    "loi": 500, "phong": 500,
    "am": 1000, "quang": 1000,
}

# ══════════════════════════════════════════════════════
#  YÊU THÚ
# ══════════════════════════════════════════════════════
YEU_THU: list[dict[str, Any]] = [
    {"id": 0, "ten": "Hỏa Hồ",        "emoji": "🦊", "cap": "Phàm", "at_bonus": 15,  "df_bonus": 0,   "hp_bonus": 50,   "rate": 40},
    {"id": 1, "ten": "Băng Sói",       "emoji": "🐺", "cap": "Phàm", "at_bonus": 20,  "df_bonus": 5,   "hp_bonus": 80,   "rate": 30},
    {"id": 2, "ten": "Lôi Ưng",        "emoji": "🦅", "cap": "Linh", "at_bonus": 40,  "df_bonus": 10,  "hp_bonus": 100,  "rate": 15},
    {"id": 3, "ten": "Hắc Kỳ Lân",     "emoji": "🦄", "cap": "Linh", "at_bonus": 60,  "df_bonus": 20,  "hp_bonus": 150,  "rate": 8},
    {"id": 4, "ten": "Thanh Long",      "emoji": "🐉", "cap": "Tiên", "at_bonus": 120, "df_bonus": 50,  "hp_bonus": 300,  "rate": 3},
    {"id": 5, "ten": "Phượng Hoàng",    "emoji": "🦚", "cap": "Tiên", "at_bonus": 100, "df_bonus": 80,  "hp_bonus": 500,  "rate": 2},
    {"id": 6, "ten": "Hỗn Độn Thú",     "emoji": "🌌", "cap": "Thần", "at_bonus": 250, "df_bonus": 150, "hp_bonus": 1000, "rate": 1},
    {"id": 7, "ten": "Bàn Cổ Linh Quy", "emoji": "🐢", "cap": "Thần", "at_bonus": 150, "df_bonus": 300, "hp_bonus": 2000, "rate": 1},
]

YEU_THU_CAP_MU: dict[str, str] = {"Phàm": "⬜", "Linh": "🟦", "Tiên": "🟨", "Thần": "🟥"}

# ══════════════════════════════════════════════════════
#  SỦNG THÚ — 9 hệ × 2 tier = 18 sủng thú
# ══════════════════════════════════════════════════════
SUNG_THU: list[dict[str, Any]] = [
    # ── Kim — ATK + Bạo Kích ──────────────────────────────────────────────────
    {"id": 0,  "he": "kim",   "tier": 1, "ten": "Kim Si Đại Bằng",    "emoji": "🦅",
     "mo_ta": "Đại bàng kim loại khổng lồ, cánh chém sắt thép",
     "drop_bc": True,  "drop_boss": False, "drop_rate": 0.05},
    {"id": 1,  "he": "kim",   "tier": 2, "ten": "Kim Sát Hổ",         "emoji": "🐯",
     "mo_ta": "Hổ vàng huyền thoại, móng vuốt xuyên thủng mọi phòng thủ",
     "drop_bc": False, "drop_boss": True,  "drop_rate": 0.008},
    # ── Mộc — Drop + EXP ────────────────────────────────────────────────────
    {"id": 2,  "he": "moc",   "tier": 1, "ten": "Tử Mộc Điệp",       "emoji": "🦋",
     "mo_ta": "Bướm tím linh thiêng, mang lại may mắn và tài lộc",
     "drop_bc": True,  "drop_boss": False, "drop_rate": 0.05},
    {"id": 3,  "he": "moc",   "tier": 2, "ten": "Vạn Niên Thụ",      "emoji": "🌳",
     "mo_ta": "Cây thần sống vạn năm, tích tụ linh khí đất trời",
     "drop_bc": False, "drop_boss": True,  "drop_rate": 0.008},
    # ── Thủy — HP + Hộ Tâm ──────────────────────────────────────────────────
    {"id": 4,  "he": "thuy",  "tier": 1, "ten": "Côn Bằng",          "emoji": "🐋",
     "mo_ta": "Cá voi linh khí, lưng rộng như núi, sức mạnh vô biên",
     "drop_bc": True,  "drop_boss": False, "drop_rate": 0.05},
    {"id": 5,  "he": "thuy",  "tier": 2, "ten": "Huyền Vũ",          "emoji": "🐢",
     "mo_ta": "Thần quy huyền thoại, mai giáp không gì phá nổi",
     "drop_bc": False, "drop_boss": True,  "drop_rate": 0.008},
    # ── Hỏa — ATK + Hội Tâm ─────────────────────────────────────────────────
    {"id": 6,  "he": "hoa",   "tier": 1, "ten": "Bất Tử Hỏa Phượng", "emoji": "🦚",
     "mo_ta": "Phượng hoàng lửa bất tử, thiêu đốt kẻ thù không ngừng",
     "drop_bc": True,  "drop_boss": False, "drop_rate": 0.05},
    {"id": 7,  "he": "hoa",   "tier": 2, "ten": "Nam Minh Chu Tước",  "emoji": "🦜",
     "mo_ta": "Thần điểu phương Nam, ngọn lửa thiêu cháy cả trời xanh",
     "drop_bc": False, "drop_boss": True,  "drop_rate": 0.008},
    # ── Thổ — DEF + Kháng Bạo ───────────────────────────────────────────────
    {"id": 8,  "he": "tho",   "tier": 1, "ten": "Cổ Hùng Trấn Ngục", "emoji": "🐻",
     "mo_ta": "Hùng thần cổ đại, trấn giữ địa ngục từ thượng cổ",
     "drop_bc": True,  "drop_boss": False, "drop_rate": 0.05},
    {"id": 9,  "he": "tho",   "tier": 2, "ten": "Thổ Tượng Chấn Địa","emoji": "🐘",
     "mo_ta": "Thần tượng đất, mỗi bước chân rung chuyển đại địa",
     "drop_bc": False, "drop_boss": True,  "drop_rate": 0.008},
    # ── Phong — DEF + Kháng Bạo + Hộ Tâm ───────────────────────────────────
    {"id": 10, "he": "phong", "tier": 1, "ten": "Thanh Phong Dực Long","emoji": "🐲",
     "mo_ta": "Rồng gió xanh, bay nhanh như chớp giữa cơn bão",
     "drop_bc": True,  "drop_boss": False, "drop_rate": 0.05},
    {"id": 11, "he": "phong", "tier": 2, "ten": "Phong Ảnh Sát Lang",  "emoji": "🐺",
     "mo_ta": "Sói gió huyền thoại, ẩn hiện trong bóng gió không thể nhìn thấy",
     "drop_bc": False, "drop_boss": True,  "drop_rate": 0.008},
    # ── Lôi — ATK + Bạo Kích mạnh nhất ─────────────────────────────────────
    {"id": 12, "he": "loi",   "tier": 1, "ten": "Tử Lôi Sư Bằng",   "emoji": "🦁",
     "mo_ta": "Sư tử sấm sét, tiếng gầm mang sức mạnh lôi đình",
     "drop_bc": True,  "drop_boss": False, "drop_rate": 0.05},
    {"id": 13, "he": "loi",   "tier": 2, "ten": "Lôi Đình Cự Nhân",  "emoji": "⚡",
     "mo_ta": "Thần nhân sấm sét, thân hình khổng lồ tích điện thiên hạ",
     "drop_bc": False, "drop_boss": True,  "drop_rate": 0.008},
    # ── Quang — EXP + Drop ───────────────────────────────────────────────────
    {"id": 14, "he": "quang", "tier": 1, "ten": "Diêu Quang Thố",    "emoji": "🐇",
     "mo_ta": "Thỏ ánh sáng thần tốc, mang theo may mắn khắp nơi",
     "drop_bc": True,  "drop_boss": False, "drop_rate": 0.05},
    {"id": 15, "he": "quang", "tier": 2, "ten": "Cửu Vĩ Thiên Hồ",   "emoji": "🦊",
     "mo_ta": "Hồ ly chín đuôi thiên thượng, trí tuệ và ánh sáng vô biên",
     "drop_bc": False, "drop_boss": True,  "drop_rate": 0.008},
    # ── Ám — Bạo Kích + Sát thương boss ─────────────────────────────────────
    {"id": 16, "he": "am",    "tier": 1, "ten": "Xích Nha Hắc Ám",   "emoji": "🦇",
     "mo_ta": "Dơi đen răng đỏ, kẻ sát thủ bóng tối không ai thấy",
     "drop_bc": True,  "drop_boss": False, "drop_rate": 0.05},
    {"id": 17, "he": "am",    "tier": 2, "ten": "Thiên Dạ Ma Long",   "emoji": "🐉",
     "mo_ta": "Rồng ma thiên dạ, bóng tối nuốt chửng ánh sáng cuối cùng",
     "drop_bc": False, "drop_boss": True,  "drop_rate": 0.008},
]

SUNG_THU_BY_ID: dict[int, dict[str, Any]]  = {st["id"]: st for st in SUNG_THU}
SUNG_THU_BY_HE: dict[str, list[dict[str, Any]]] = {}
for st in SUNG_THU:
    SUNG_THU_BY_HE.setdefault(st["he"], []).append(st)

# Buff cơ bản theo hệ (per level, nhân với SUNG_THU_LEVEL_MULT)
# Buff cơ bản theo hệ (per level, nhân với SUNG_THU_LEVEL_MULT)
# Thiết kế: mỗi hệ có vai trò rõ ràng, không chồng chéo quá nhiều
# Base value là khi level 1. Level 10 × 6.5 = giá trị tối đa
SUNG_THU_HE_BUFF: dict[str, dict[str, Any]] = {
    "kim":   {"at_pct": 2.0, "bao_kich": 1.5},           # DPS: ATK + crit
    "moc":   {"drop_rate": 3.5, "exp_pct": 3.5},          # Farm: drop + EXP
    "thuy":  {"hp_pct": 3.5, "ho_tam": 120},               # Tank: HP + giảm crit nhận
    "hoa":   {"at_pct": 2.0, "hoi_tam": 200},              # DPS: ATK + Hội Tâm (crit rate)
    "tho":   {"def_pct": 3.5, "khang_bao": 2.0},           # Tank: DEF + Kháng Bạo
    "phong": {"def_pct": 2.0, "khang_bao": 1.5, "ho_tam": 80},  # Hybrid tank
    "loi":   {"at_pct": 1.5, "bao_kich": 2.5},            # DPS: crit-focused
    "quang": {"exp_pct": 3.5, "drop_rate": 2.0},           # Farm: EXP + chút drop
    "am":    {"bao_kich": 3.0, "at_pct": 1.0},             # DPS: crit dmg + ít ATK
}

# Set bonus khi sủng thú cùng hệ linh căn — giảm xuống để không broken
SUNG_THU_SET_BONUS: dict[str, dict[str, Any]] = {
    "kim":   {"at_pct": 8.0},
    "moc":   {"drop_rate": 8.0},
    "thuy":  {"hp_pct": 10.0},
    "hoa":   {"hoi_tam": 300},
    "tho":   {"def_pct": 10.0},
    "phong": {"khang_bao": 5.0, "ho_tam": 200},
    "loi":   {"bao_kich": 4.0},
    "quang": {"exp_pct": 10.0},
    "am":    {"boss_dmg_pct": 8.0},
}

# Skill chiến đấu
SUNG_THU_SKILL: dict[str, dict[str, Any]] = {
    "kim":   {"passive": {"ten": "Thép Hóa",     "mo_ta": "10% cộng Bạo Kích mỗi đòn"},
              "active":  {"ten": "Kim Sát Trảm",  "mo_ta": "Tấn công phụ 30% AT", "cd": 4, "dmg_pct": 0.30}},
    "moc":   {"passive": {"ten": "Sinh Sôi",      "mo_ta": "Tăng 5% Drop mỗi phòng"},
              "active":  {"ten": "Sinh Mộc Trận", "mo_ta": "Hồi 8% HP tối đa", "cd": 5, "heal_pct": 0.08}},
    "thuy":  {"passive": {"ten": "Huyền Băng",    "mo_ta": "Giảm 5% sát thương nhận vào"},
              "active":  {"ten": "Hàn Lưu Khiên", "mo_ta": "Shield 15% HP trong 2 lượt", "cd": 6, "shield_pct": 0.15}},
    "hoa":   {"passive": {"ten": "Hỏa Linh",      "mo_ta": "Tăng 10% Hội Tâm khi đánh"},
              "active":  {"ten": "Viêm Bùng",      "mo_ta": "Tấn công phụ 25% AT", "cd": 4, "dmg_pct": 0.25}},
    "tho":   {"passive": {"ten": "Địa Cương",      "mo_ta": "Tăng 8% DEF thường trực"},
              "active":  {"ten": "Trấn Ngục Trận", "mo_ta": "Shield 20% HP trong 3 lượt", "cd": 7, "shield_pct": 0.20}},
    "phong": {"passive": {"ten": "Phong Tốc",      "mo_ta": "Tăng 10% Kháng Bạo"},
              "active":  {"ten": "Phong Nhận",      "mo_ta": "Tấn công phụ 20% AT × 2 đòn", "cd": 4, "dmg_pct": 0.20, "hits": 2}},
    "loi":   {"passive": {"ten": "Lôi Thể",        "mo_ta": "Tăng 15% Bạo Kích"},
              "active":  {"ten": "Lôi Đình Kích",   "mo_ta": "Tấn công phụ 50% AT", "cd": 6, "dmg_pct": 0.50}},
    "quang": {"passive": {"ten": "Quang Chiếu",     "mo_ta": "Tăng 10% EXP nhận được"},
              "active":  {"ten": "Thiên Quang Trận","mo_ta": "Hồi 5% HP + AT +10% trong 3 lượt", "cd": 5, "heal_pct": 0.05, "at_buff": 0.10}},
    "am":    {"passive": {"ten": "Ám Sát",          "mo_ta": "Tăng 20% sát thương lên boss"},
              "active":  {"ten": "Hắc Ám Xuyên",    "mo_ta": "Tấn công phụ 40% AT, xuyên 30% DEF", "cd": 5, "dmg_pct": 0.40, "pen_pct": 0.30}},
}

# Hệ số buff theo level
# Hệ số buff theo level — tăng đều, cap hợp lý hơn
SUNG_THU_LEVEL_MULT: dict[int, float] = {1:1.0, 2:1.25, 3:1.55, 4:1.90, 5:2.30,
                       6:2.75, 7:3.25, 8:3.80, 9:4.40, 10:5.0}
SUNG_THU_TIER2_MULT = 1.6  # Tier 2 mạnh hơn 1.6× (giảm từ 1.8×)

# Nguyên liệu nâng cấp (key = level muốn đạt)
# Tier 1 (Thường) — cost cơ bản
SUNG_THU_LEVELUP_COST = {
    2:  {"0": 3, "1": 1},
    3:  {"0": 5, "1": 2},
    4:  {"1": 3, "2": 1},
    5:  {"1": 5, "2": 3},
    6:  {"2": 4, "3": 2},
    7:  {"2": 6, "3": 3},
    8:  {"3": 4, "4": 2},
    9:  {"3": 6, "4": 4},
    10: {"4": 5, "5": 3},
}

# Tier 2 (Huyền Thoại) — cost ×10 so với Tier 1, tăng thêm 20% mỗi cấp
SUNG_THU_LEVELUP_COST_T2 = {
    2:  {"0": 30, "1": 10},
    3:  {"0": 60, "1": 25},
    4:  {"1": 45, "2": 15},
    5:  {"1": 90, "2": 50},
    6:  {"2": 80, "3": 40},
    7:  {"2": 150, "3": 70},
    8:  {"3": 120, "4": 60},
    9:  {"3": 210, "4": 140},
    10: {"4": 210, "5": 130},
}

# Yêu cầu cảnh giới để nâng cấp sủng thú lên level nhất định
# Key = level đích, value = canh_gioi tối thiểu
SUNG_THU_LEVELUP_CG_YEU_CAU = {
    1:  0,   # Mọi người đều có thể có Lv1
    2:  0,   # Lv2 — không yêu cầu
    3:  0,   # Lv3 — không yêu cầu
    4:  1,   # Lv4 — yêu cầu Trúc Cơ
    5:  2,   # Lv5 — yêu cầu Kết Tinh
    6:  3,   # Lv6 — yêu cầu Kim Đan
    7:  4,   # Lv7 — yêu cầu Cụ Linh
    8:  5,   # Lv8 — yêu cầu Nguyên Anh
    9:  6,   # Lv9 — yêu cầu Hóa Thần
    10: 7,   # Lv10 — yêu cầu Ngộ Đạo
}

# ══════════════════════════════════════════════════════════════
#  BÍ CẢNH
# ══════════════════════════════════════════════════════════════
SU_KIEN_BI_CANH = [
    {"id": "bau_vat",   "ten": "Phát Hiện Bảo Vật!", "emoji": "💎", "loai": "reward",
     "mo_ta": "Ngươi tìm thấy một rương bảo vật bí ẩn giữa đường...",
     "lt_bonus": 0.3, "hp_bonus": 0.0, "exp_bonus": 0.0},
    {"id": "linh_tuyen","ten": "Gặp Linh Tuyền!",    "emoji": "💧", "loai": "reward",
     "mo_ta": "Một dòng suối linh khí hiện ra, hồi phục nguyên khí...",
     "lt_bonus": 0.0, "hp_bonus": 0.3, "exp_bonus": 0.0},
    {"id": "co_dan",    "ten": "Tìm Thấy Cổ Đan!",   "emoji": "💊", "loai": "reward",
     "mo_ta": "Một viên đan dược cổ xưa nằm trong kẽ đá...",
     "lt_bonus": 0.0, "hp_bonus": 0.0, "exp_bonus": 0.4},
    {"id": "bay_tran",  "ten": "Dính Bẫy Trận!",     "emoji": "🪤", "loai": "trap",
     "mo_ta": "Cẩn thận! Ngươi vô tình kích hoạt bẫy trận bí ẩn!", "hp_mat": 0.15},
    {"id": "quy_khi",   "ten": "Bị Quỷ Khí Xâm Nhập!","emoji": "👻","loai": "trap",
     "mo_ta": "Quỷ khí tràn vào kinh mạch, nguyên lực tổn thất...", "hp_mat": 0.1, "lt_mat": 0.1},
    {"id": "linh_tho",  "ten": "Gặp Linh Thú Lang Thang!","emoji": "🐾","loai": "combat_bonus",
     "mo_ta": "Một linh thú yếu lang thang, ngươi dễ dàng thu phục...", "yeu_thu_bonus": True},
]

# ══════════════════════════════════════════════════════
#  ĐAN TU LUYỆN
# ══════════════════════════════════════════════════════
_DTL_GIA = [1500, 3500, 8000, 18000, 40000, 90000, 200000, 450000, 1000000, 2200000]

DAN_TU_LUYEN = [
    [{"ten": "Tụ Khí",   "emoji": E_TUKHI,  "cap_nho_sau": 2, "rate": 0.05, "gia": _DTL_GIA[0]},
     {"ten": "Tập Khí",  "emoji": E_TAPKHI, "cap_nho_sau": 3, "rate": 0.05, "gia": _DTL_GIA[0]*2}],
    [{"ten": "Tẩy Tủy Đan",        "emoji": E_TAYTUY_THUONG, "cap_nho_sau": 2, "rate": 0.05, "gia": _DTL_GIA[1]},
     {"ten": "Tẩy Tủy Đan (Hiếm)", "emoji": E_TAYTUY_HIEM,  "cap_nho_sau": 3, "rate": 0.05, "gia": _DTL_GIA[1]*2}],
    [{"ten": "Luyện Thể Đan",        "emoji": E_LUYENTHEDAN_THUONG, "cap_nho_sau": 2, "rate": 0.05, "gia": _DTL_GIA[2]},
     {"ten": "Luyện Thể Đan (Hiếm)", "emoji": E_LUYENTHEDAN_HIEM,  "cap_nho_sau": 3, "rate": 0.05, "gia": _DTL_GIA[2]*2}],
    [{"ten": "Thông Mạch Đan", "emoji": E_THONGMACH, "cap_nho_sau": 2, "rate": 0.05, "gia": _DTL_GIA[3]},
     {"ten": "Thuận Mạch Đan", "emoji": E_THUANMACH, "cap_nho_sau": 3, "rate": 0.05, "gia": _DTL_GIA[3]*2}],
    [{"ten": "Dung Linh Đan", "emoji": E_DUNGLINH, "cap_nho_sau": 2, "rate": 0.05, "gia": _DTL_GIA[4]},
     {"ten": "Hợp Linh Đan",  "emoji": E_HOPLINH,  "cap_nho_sau": 3, "rate": 0.05, "gia": _DTL_GIA[4]*2}],
    [{"ten": "Uẩn Huyết Đan", "emoji": E_UANHUYET, "cap_nho_sau": 2, "rate": 0.05, "gia": _DTL_GIA[5]},
     {"ten": "Trữ Huyết Đan", "emoji": E_TRUHUYET, "cap_nho_sau": 3, "rate": 0.05, "gia": _DTL_GIA[5]*2}],
    [{"ten": "Ngưng Thần Đan",   "emoji": E_NGUNGTHAN,   "cap_nho_sau": 2, "rate": 0.05, "gia": _DTL_GIA[6]},
     {"ten": "Thăng Nguyên Đan", "emoji": E_THANGNGUYEN, "cap_nho_sau": 3, "rate": 0.05, "gia": _DTL_GIA[6]*2}],
    [{"ten": "Hoàn Nguyên Đan",  "emoji": E_HOANNGUYEN,  "cap_nho_sau": 2, "rate": 0.05, "gia": _DTL_GIA[7]},
     {"ten": "Thăng Nguyên Đan", "emoji": E_THANGNGUYEN, "cap_nho_sau": 3, "rate": 0.05, "gia": _DTL_GIA[7]*2}],
    [{"ten": "Hỗn Độn Chi Tức",              "emoji": E_HONDONCHITUC,       "cap_nho_sau": 2, "rate": 0.05, "gia": _DTL_GIA[8]},
     {"ten": "Hỗn Độn Linh Tức",             "emoji": E_HONDONLINHTUC,      "cap_nho_sau": 2, "rate": 0.05, "gia": _DTL_GIA[8]},
     {"ten": "Thượng Phẩm Hỗn Độn Linh Tức", "emoji": E_HONDONCHITUC_HIEM, "cap_nho_sau": 3, "rate": 0.05, "gia": _DTL_GIA[8]*2},
     {"ten": "Thanh Tịnh Linh Tức",          "emoji": E_THANHTINHLINHTUC,   "cap_nho_sau": 3, "rate": 0.05, "gia": _DTL_GIA[8]*2}],
    [{"ten": "Tiên Thiên Nhất Khí - Yếu",  "emoji": E_TIENTHIENNHATKHI_THUONG, "cap_nho_sau": 2, "rate": 0.05, "gia": _DTL_GIA[9]},
     {"ten": "Tiên Thiên Nhất Khí - Sinh", "emoji": E_TIENTHIENNHATKHI_HIEM,   "cap_nho_sau": 3, "rate": 0.05, "gia": _DTL_GIA[9]*2}],
]

# ══════════════════════════════════════════════════════
#  ĐIỂM DANH
# ══════════════════════════════════════════════════════
DIEM_DANH_PHAN_THUONG = [
    {"ngay": 1, "lt": 1500,  "exp": 150},
    {"ngay": 2, "lt": 1800,  "exp": 180},
    {"ngay": 3, "lt": 2250,  "exp": 225},
    {"ngay": 4, "lt": 2700,  "exp": 270},
    {"ngay": 5, "lt": 3300,  "exp": 330},
    {"ngay": 6, "lt": 3900,  "exp": 390},
    {"ngay": 7, "lt": 9000,  "exp": 900},
]

# ══════════════════════════════════════════════════════
#  PHÁP BẢO KỸ NĂNG (passive trigger trong bi_canh combat)
# ══════════════════════════════════════════════════════
PHAP_BAO_SKILL = {
    0: {"ten": "Giác Kỳ Thần Âm",
        "mo_ta": "Khi HP < 50%: tăng AT +30% trong 3 lượt (CD 8 lượt)",
        "trigger": "hp_below", "threshold": 0.50,
        "effect": "at_buff", "buff_pct": 0.30, "duration": 3, "cd": 8},
    1: {"ten": "Hoàng Cực Hộ Thể",
        "mo_ta": "Mỗi 5 lượt: hấp thụ 20% sát thương nhận trong 1 lượt (CD 5 lượt)",
        "trigger": "every_n", "n": 5,
        "effect": "dmg_absorb", "absorb_pct": 0.20, "duration": 1, "cd": 5},
    2: {"ten": "Tinh Chùy Phá Giáp",
        "mo_ta": "Mỗi đòn đánh: 30% xác suất giảm DEF quái 20% trong 2 lượt (CD 3 lượt)",
        "trigger": "on_hit", "chance": 0.30,
        "effect": "def_shred", "shred_pct": 0.20, "duration": 2, "cd": 3},
    3: {"ten": "Huyền Chung Tịnh Hóa",
        "mo_ta": "Khi nhận bạo kích: phản sát 15% ATK địch (CD 4 lượt)",
        "trigger": "on_crit_recv",
        "effect": "counter", "counter_pct": 0.15, "cd": 4},
    4: {"ten": "Huyết Diện Cuồng Sát",
        "mo_ta": "Bạo kích của ta được nhân thêm ×1.5 (×1.8 → ×2.7)",
        "trigger": "passive",
        "effect": "crit_amplify", "extra_mult": 1.5, "cd": 0},
    5: {"ten": "Chi Kỳ Trận Thế",
        "mo_ta": "Đầu trận: tăng AT và DEF +15% trong 5 lượt đầu (1 lần/trận)",
        "trigger": "battle_start",
        "effect": "at_df_buff", "buff_pct": 0.15, "duration": 5, "cd": 99},
    6: {"ten": "Ngưng Châu Hồi Nguyên",
        "mo_ta": "Mỗi 4 lượt: hồi 8% HP tối đa",
        "trigger": "every_n", "n": 4,
        "effect": "heal", "heal_pct": 0.08, "cd": 4},
    7: {"ten": "Bạch Bào Thiết Phòng",
        "mo_ta": "Khi HP < 30%: miễn sát thương 1 lượt (CD 10 lượt)",
        "trigger": "hp_below", "threshold": 0.30,
        "effect": "invincible", "duration": 1, "cd": 10},
    8: {"ten": "Thiết Bích Kim Cương",
        "mo_ta": "Mỗi đòn nhận: 20% xác suất block toàn bộ sát thương (CD 3 lượt)",
        "trigger": "on_recv", "chance": 0.20,
        "effect": "full_block", "cd": 3},
    9: {"ten": "Cổ Cầm Huyễn Âm",
        "mo_ta": "Mỗi 3 lượt: tấn công thêm 1 đòn phụ (40% ATK)",
        "trigger": "every_n", "n": 3,
        "effect": "extra_attack", "extra_pct": 0.40, "cd": 3},
}

# ══════════════════════════════════════════════════════
#  QUAN HỆ
# ══════════════════════════════════════════════════════
QUAN_HE_MOC_DUONG = [
    {"diem": 100,  "ten": "Sơ Giao",    "emoji": "🤝", "ket_giao": []},
    {"diem": 300,  "ten": "Quen Biết",  "emoji": "😊", "ket_giao": ["bang_huu"]},
    {"diem": 600,  "ten": "Thân Thiết", "emoji": "💛", "ket_giao": ["huynh","de","ti","muoi"]},
    {"diem": 1000, "ten": "Tri Kỉ",     "emoji": "💜", "ket_giao": ["tri_ki"]},
]
QUAN_HE_MOC_AM = [
    {"diem": -100,  "ten": "Ghen Tị",              "emoji": "😒"},
    {"diem": -300,  "ten": "Thù Địch",              "emoji": "😠"},
    {"diem": -600,  "ten": "Cừu Hận",               "emoji": "🔥"},
    {"diem": -1000, "ten": "Không Chết Không Thôi",  "emoji": "💀"},
]
QUAN_HE_LOAI = {
    "bang_huu": {"ten": "Bằng Hữu", "emoji": "🤝", "yeu_cau": 300},
    "huynh":    {"ten": "Huynh",    "emoji": "👦", "yeu_cau": 600},
    "de":       {"ten": "Đệ",       "emoji": "👦", "yeu_cau": 600},
    "ti":       {"ten": "Tỉ",       "emoji": "👧", "yeu_cau": 600},
    "muoi":     {"ten": "Muội",     "emoji": "👧", "yeu_cau": 600},
    "tri_ki":   {"ten": "Tri Kỉ",   "emoji": "💜", "yeu_cau": 1000},
}
TANG_QUA_DIEM_MAX_NGAY = 100
TANG_QUA_LT_MAX        = 10000
TANG_QUA_LT_PER_DIEM   = 100
TANG_QUA_DAN_PER_DIEM  = 20

# ══════════════════════════════════════════════════════════════
#  TÀI NGUYÊN ĐỘT PHÁ THỂ CHẤT
# ══════════════════════════════════════════════════════════════
DOTPHA_TC_NGUYEN_LIEU: list[dict[str, Any]] = [
    {"id": "tuloicamquy",     "ten": "Tụ Lôi Cẩm Quỳ",    "emoji": "<:tuloicamquy:1483262173047427083>",     "nguon": "boss"},
    {"id": "huyethonxahuong","ten": "Huyết Hồn Xạ Hương", "emoji": "<:huyethonxahuong:1483262171982069820>", "nguon": "bi_canh"},
    {"id": "coctructang",    "ten": "Cốc Trúc Tang",       "emoji": "<:coctructang:1483262170849607802>",     "nguon": "boss"},
    {"id": "ngungcannhu",    "ten": "Ngưng Càn Nhũ",       "emoji": "<:ngungcannhu:1483262169272291420>",     "nguon": "bi_canh"},
    {"id": "huyetchihoalinh","ten": "Huyết Chi Hỏa Linh",  "emoji": "<:huyetchihoalinh:1483262168274305176>", "nguon": "boss_bi_canh"},
]
DOTPHA_TC_DROP_RATE = 0.002  # Drop thấp — nguyên liệu hiếm
DOTPHA_TC_POOL: dict[str, list[str]] = {
    "low":  ["cuu_bien_kim_the","thien_menh_linh_the","bang_hoa_song_the"],
    "mid":  ["cuu_bien_kim_the","thien_menh_linh_the","bang_hoa_song_the",
             "loi_nguc_than_the","huyen_am_ma_the","thai_duong_dao_the"],
    "apex": ["cuu_bien_kim_the","thien_menh_linh_the","bang_hoa_song_the",
             "loi_nguc_than_the","huyen_am_ma_the","thai_duong_dao_the",
             "hon_don_thanh_the","vo_thuy_tien_the"],
}
# Rate override cho pool apex — Hỗn Độn/Vô Thủy dùng 5% thay vì 0.2%
DOTPHA_TC_APEX_RATE_OVERRIDE: dict[str, float] = {
    "hon_don_thanh_the": 5.0,
    "vo_thuy_tien_the":  5.0,
}
DOTPHA_TC_NL_BY_ID = {nl["id"]: nl for nl in DOTPHA_TC_NGUYEN_LIEU}

# ── Shop / Promo Code Config ────────────────────────────────────────────────
SHOP_QR_1: str = "assets/qr1.jpg"   # VietinBank — TRẦN THỊ THANH XUÂN
SHOP_QR_2: str = "assets/qr2.jpg"   # VIB — ĐỖ PHƯƠNG NAM
SHOP_CONTACT_ID: int = 182542306715369472  # Gửi bill xác nhận tại đây

SHOP_PACKAGES: dict[str, dict[str, Any]] = {
    "dot_pha_tc": {
        "ten": "5 Đột Phá Thể Chất",
        "mo_ta": "5 nguyên liệu đột phá thân cấp (mỗi loại ×1)",
        "gia": 100000,
        "emoji": "💎",
    },
    "ngu_hanh_qua": {
        "ten": "5 Ngũ Hành Linh Quả (Hỏa Thủy Thổ Mộc Kim)",
        "mo_ta": "5 loại linh quả ngũ hành cơ bản (mỗi loại ×30 quả)",
        "gia": 50000,
        "emoji": "🍎",
    },
    "nguyen_to_qua": {
        "ten": "4 Nguyên Tố Linh Quả (Phong Lôi Quang Ám)",
        "mo_ta": "4 loại linh quả nguyên tố hiếm (mỗi loại ×30 quả)",
        "gia": 80000,
        "emoji": "🌀",
    },
    "phap_bao": {
        "ten": "Pháp Bảo Ngẫu Nhiên (Cảnh Giới Tuỳ May)",
        "mo_ta": "1 pháp bảo ngẫu nhiên bất kỳ",
        "gia": 80000,
        "emoji": "⚔️",
    },
}

SHOP_PACKAGE_IDS: list[str] = list(SHOP_PACKAGES.keys())
