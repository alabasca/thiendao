from __future__ import annotations
from typing import Any

BI_CANH = [
    # BC0 — Luyện Khí trở lên. Quái HP tăng 3× để không one-shot với công pháp.
    {"id": 0, "ten": "Thạch Thất", "emoji": "🪨",
     "mo_ta": "Hang đá cổ xưa ẩn chứa linh khí nguyên thủy. Nơi khởi đầu của mọi tu sĩ Luyện Khí.",
     "cap_toi_thieu": 0,
     "phong_thuong": [
       {"ten": "Dã Trư",     "emoji": "🐗", "hp": 2200, "at": 45,  "df": 14, "hoi_tam": 350, "bao_kich": 1.4, "ho_tam": 40, "khang_bao": 0.04, "exp_min": 55,  "exp_max": 90,  "lt_min": 35, "lt_max": 60,  "nl_drop": [0]},
       {"ten": "Thạch Tinh",  "emoji": "🪨", "hp": 2800, "at": 55,  "df": 22, "hoi_tam": 400, "bao_kich": 1.5, "ho_tam": 55, "khang_bao": 0.06, "exp_min": 70,  "exp_max": 115, "lt_min": 45, "lt_max": 75,  "nl_drop": [0]},
       {"ten": "Mãnh Hổ Nhi", "emoji": "🐅", "hp": 3500, "at": 68,  "df": 20, "hoi_tam": 480, "bao_kich": 1.7, "ho_tam": 45, "khang_bao": 0.05, "exp_min": 85,  "exp_max": 140, "lt_min": 55, "lt_max": 90,  "nl_drop": [0, 1]}
       ],
     "boss": {"ten": "Bạch Cẩu", "emoji": "🐕",
       "hp": 4500, "at": 75, "df": 22, "hoi_tam": 700, "bao_kich": 1.8, "ho_tam": 100, "khang_bao": 0.08,
       "exp_min": 120, "exp_max": 200, "lt_min": 95, "lt_max": 160, "nl_drop": [0,1],
       "mo_ta": "Bạch Cẩu linh thú trấn giữ Thạch Thất, nanh vuốt sắc như kiếm!"},
     "yeu_thu_drop": [0], "yt_drop_rate": 0.05, "yt_boss_rate": 0.12},
    # BC1 — Trúc Cơ trở lên
    {"id": 1, "ten": "Quỷ Cốc", "emoji": "💀",
     "mo_ta": "Thung lũng quỷ khí bao phủ, âm khí nặng nề. Dành cho tu sĩ Trúc Cơ dày dặn kinh nghiệm.",
     "cap_toi_thieu": 1,
     "phong_thuong": [
       {"ten": "Ngạc Ngư",     "emoji": "🐊", "hp": 6200,  "at": 145, "df": 24,  "hoi_tam": 750,  "bao_kich": 1.55, "ho_tam": 90,  "khang_bao": 0.05, "exp_min": 120, "exp_max": 195, "lt_min": 48, "lt_max": 75, "nl_drop": [0, 1]},
       {"ten": "Quỷ Binh",     "emoji": "👺", "hp": 8000,  "at": 180, "df": 32,  "hoi_tam": 900,  "bao_kich": 1.65, "ho_tam": 115, "khang_bao": 0.06, "exp_min": 150, "exp_max": 250, "lt_min": 60, "lt_max": 95, "nl_drop": [0, 1]},
       {"ten": "Hắc Độc Nhện", "emoji": "🕷️", "hp": 10000, "at": 210, "df": 28,  "hoi_tam": 1050, "bao_kich": 1.80, "ho_tam": 100, "khang_bao": 0.05, "exp_min": 185, "exp_max": 305, "lt_min": 73, "lt_max": 115, "nl_drop": [1, 2]}
       ],
     "boss": {"ten": "Huyền Tinh Thạch Linh", "emoji": "💎",
       "hp": 13000, "at": 255, "df": 38, "hoi_tam": 1600, "bao_kich": 1.98, "ho_tam": 220, "khang_bao": 0.09,
       "exp_min": 500, "exp_max": 840, "lt_min": 120, "lt_max": 185, "nl_drop": [1,2],
       "mo_ta": "Thạch linh hút tinh hoa thiên địa ngàn năm, thân cứng hơn kim cương!"},
     "yeu_thu_drop": [0,1], "yt_drop_rate": 0.04, "yt_boss_rate": 0.10},
    # BC2 — Kết Tinh trở lên
    {"id": 2, "ten": "Vạn Sơn", "emoji": "⛰️",
     "mo_ta": "Vạn ngọn núi trùng điệp, linh mạch giao hội. Kết Tinh tu sĩ tôi luyện thân pháp tại đây.",
     "cap_toi_thieu": 2,
     "phong_thuong": [
       {"ten": "Sơn Linh",  "emoji": "🦌", "hp": 17000, "at": 650,  "df": 76,  "hoi_tam": 1100, "bao_kich": 1.68, "ho_tam": 135, "khang_bao": 0.06, "exp_min": 200, "exp_max": 340, "lt_min": 128, "lt_max": 192, "nl_drop": [1, 2]},
       {"ten": "Bạch Điểu", "emoji": "🦢", "hp": 22000, "at": 830,  "df": 97,  "hoi_tam": 1400, "bao_kich": 1.80, "ho_tam": 172, "khang_bao": 0.07, "exp_min": 260, "exp_max": 440, "lt_min": 165, "lt_max": 250, "nl_drop": [1, 2]},
       {"ten": "Nham Thạch Tinh", "emoji": "🗿", "hp": 27500, "at": 760,  "df": 130, "hoi_tam": 1200, "bao_kich": 1.62, "ho_tam": 200, "khang_bao": 0.09, "exp_min": 320, "exp_max": 540, "lt_min": 200, "lt_max": 305, "nl_drop": [2, 3]}
       ],
     "boss": {"ten": "Huyết Ma", "emoji": "🩸",
       "hp": 36000, "at": 1140, "df": 115, "hoi_tam": 2500, "bao_kich": 2.16, "ho_tam": 340, "khang_bao": 0.11,
       "exp_min": 430, "exp_max": 720, "lt_min": 310, "lt_max": 470, "nl_drop": [2,3],
       "mo_ta": "Huyết Ma ngàn năm tu luyện trong Vạn Sơn, toàn thân nhuốm máu hồng!"},
     "yeu_thu_drop": [1,2], "yt_drop_rate": 0.04, "yt_boss_rate": 0.09},
    # BC3 — Kim Đan trở lên
    {"id": 3, "ten": "Kiếm Trì", "emoji": "⚔️",
     "mo_ta": "Hồ kiếm khí dày đặc, mỗi giọt nước ẩn chứa kiếm ý sắc bén. Kim Đan tu sĩ mài giũa kiếm đạo.",
     "cap_toi_thieu": 3,
     "phong_thuong": [
       {"ten": "Kiếm Hồn",    "emoji": "⚔️", "hp": 40500, "at": 1300, "df": 160, "hoi_tam": 1750, "bao_kich": 1.80, "ho_tam": 185, "khang_bao": 0.07, "exp_min": 530,  "exp_max": 890,  "lt_min": 320, "lt_max": 485, "nl_drop": [2, 3]},
       {"ten": "Cửu Đầu Xà", "emoji": "🐍", "hp": 52000, "at": 1650, "df": 202, "hoi_tam": 2200, "bao_kich": 1.95, "ho_tam": 232, "khang_bao": 0.08, "exp_min": 680,  "exp_max": 1140, "lt_min": 410, "lt_max": 620, "nl_drop": [2, 3]},
       {"ten": "Thiết Giáp Kỳ Lân", "emoji": "🦄", "hp": 64500, "at": 1900, "df": 250, "hoi_tam": 2650, "bao_kich": 2.10, "ho_tam": 270, "khang_bao": 0.09, "exp_min": 840,  "exp_max": 1400, "lt_min": 505, "lt_max": 760, "nl_drop": [3, 4]}
       ],
     "boss": {"ten": "Đương Khang", "emoji": "🦌",
       "hp": 83000, "at": 2280, "df": 250, "hoi_tam": 3800, "bao_kich": 2.34, "ho_tam": 460, "khang_bao": 0.12,
       "exp_min": 1100, "exp_max": 1840, "lt_min": 760, "lt_max": 1140, "nl_drop": [3,4],
       "mo_ta": "Đương Khang linh thú cổ đại, sừng vàng chứa đựng kiếm ý thiên hà!"},
     "yeu_thu_drop": [2,3], "yt_drop_rate": 0.03, "yt_boss_rate": 0.08},
    # BC4 — Cụ Linh trở lên
    {"id": 4, "ten": "U Uẩn Cốc", "emoji": "🌫️",
     "mo_ta": "Thung lũng u uẩn bí ẩn, sương mù không tan. Cụ Linh tu sĩ thường lạc lối không tìm được lối ra.",
     "cap_toi_thieu": 4,
     "phong_thuong": [
       {"ten": "Ẩn Ảo Nhân",    "emoji": "👻", "hp": 91500,  "at": 2450, "df": 320, "hoi_tam": 2350, "bao_kich": 1.95, "ho_tam": 235, "khang_bao": 0.08, "exp_min": 1030, "exp_max": 1715, "lt_min": 780,  "lt_max": 1170, "nl_drop": [3, 4]},
       {"ten": "Hải Thạch Quy",  "emoji": "🐢", "hp": 118000, "at": 3100, "df": 403, "hoi_tam": 3000, "bao_kich": 2.10, "ho_tam": 292, "khang_bao": 0.09, "exp_min": 1320, "exp_max": 2200, "lt_min": 1000, "lt_max": 1500, "nl_drop": [3, 4]},
       {"ten": "Huyết Yết Tinh", "emoji": "🦂", "hp": 148000, "at": 3700, "df": 460, "hoi_tam": 3600, "bao_kich": 2.28, "ho_tam": 340, "khang_bao": 0.10, "exp_min": 1620, "exp_max": 2700, "lt_min": 1230, "lt_max": 1845, "nl_drop": [4, 5]}
       ],
     "boss": {"ten": "Lục Vĩ Hồ", "emoji": "🦊",
       "hp": 192000, "at": 4350, "df": 500, "hoi_tam": 5500, "bao_kich": 2.52, "ho_tam": 580, "khang_bao": 0.14,
       "exp_min": 2150, "exp_max": 3600, "lt_min": 1850, "lt_max": 2800, "nl_drop": [4,5],
       "mo_ta": "Lục Vĩ Hồ ngàn tuổi, sáu chiếc đuôi mang phép thuật mê hoặc vô song!"},
     "yeu_thu_drop": [3,4], "yt_drop_rate": 0.03, "yt_boss_rate": 0.07},
    # BC5 — Nguyên Anh trở lên
    {"id": 5, "ten": "Vô Cực Chi Cảnh", "emoji": "♾️",
     "mo_ta": "Cảnh giới không có điểm cuối, không gian vô tận. Nguyên Anh tu sĩ cảm ngộ đạo pháp tại đây.",
     "cap_toi_thieu": 5,
     "phong_thuong": [
       {"ten": "Không Gian Quỷ", "emoji": "🌀", "hp": 185000, "at": 7500,  "df": 1000, "hoi_tam": 3300, "bao_kich": 2.10, "ho_tam": 280, "khang_bao": 0.09, "exp_min": 2480, "exp_max": 4130, "lt_min": 1870, "lt_max": 2800, "nl_drop": [4, 5]},
       {"ten": "Thiết Vũ Ưng",   "emoji": "🦅", "hp": 240000, "at": 9600,  "df": 1310, "hoi_tam": 4200, "bao_kich": 2.25, "ho_tam": 353, "khang_bao": 0.10, "exp_min": 3200, "exp_max": 5300, "lt_min": 2400, "lt_max": 3600, "nl_drop": [4, 5]},
       {"ten": "Hư Linh Thú",    "emoji": "🌫️", "hp": 300000, "at": 11200, "df": 1550, "hoi_tam": 5000, "bao_kich": 2.43, "ho_tam": 415, "khang_bao": 0.11, "exp_min": 3940, "exp_max": 6560, "lt_min": 2960, "lt_max": 4440, "nl_drop": [5, 6]}
       ],
     "boss": {"ten": "Nhân Diện Điểu", "emoji": "🦜",
       "hp": 390000, "at": 13500, "df": 1600, "hoi_tam": 7500, "bao_kich": 2.7, "ho_tam": 700, "khang_bao": 0.15,
       "exp_min": 5200, "exp_max": 8700, "lt_min": 4400, "lt_max": 6600, "nl_drop": [5,6],
       "mo_ta": "Nhân Diện Điểu dị thú cổ đại, mặt người mình chim, tri tuệ hơn cả thần tiên!"},
     "yeu_thu_drop": [4,5], "yt_drop_rate": 0.02, "yt_boss_rate": 0.06},
    # BC6 — Hóa Thần (giữ nguyên từ BC6+ vì AT người chơi cũng tăng mạnh)
    {"id": 6, "ten": "Minh Chủng U Huyệt", "emoji": "🕳️",
     "mo_ta": "Huyệt đạo tối tăm ẩn chứa hạt giống của minh giới. Hóa Thần tu sĩ đối mặt với bóng tối nội tâm.",
     "cap_toi_thieu": 6,
     "phong_thuong": [
       {"ten": "Minh Giới Binh",   "emoji": "💀", "hp": 375000, "at": 16000, "df": 2200, "hoi_tam": 4300, "bao_kich": 2.24, "ho_tam": 325, "khang_bao": 0.10, "exp_min": 5460,  "exp_max": 9100,  "lt_min": 4060, "lt_max": 6090, "nl_drop": [5, 6]},
       {"ten": "Huyết Cuồng Lang", "emoji": "🐺", "hp": 480000, "at": 20500, "df": 2820, "hoi_tam": 5500, "bao_kich": 2.40, "ho_tam": 413, "khang_bao": 0.11, "exp_min": 7000,  "exp_max": 11700, "lt_min": 5200, "lt_max": 7800, "nl_drop": [5, 6]},
       {"ten": "Hắc Yêu Ma",       "emoji": "😈", "hp": 600000, "at": 24000, "df": 3300, "hoi_tam": 6500, "bao_kich": 2.59, "ho_tam": 480, "khang_bao": 0.12, "exp_min": 8640,  "exp_max": 14400, "lt_min": 6430, "lt_max": 9640, "nl_drop": [6, 7]}
       ],
     "boss": {"ten": "Lân Ngư", "emoji": "🐟",
       "hp": 780000, "at": 28800, "df": 3400, "hoi_tam": 9500, "bao_kich": 2.88, "ho_tam": 820, "khang_bao": 0.17,
       "exp_min": 11400, "exp_max": 19000, "lt_min": 9600, "lt_max": 14400, "nl_drop": [6,7],
       "mo_ta": "Lân Ngư thần thú trú tại U Huyệt, vảy cứng hơn vạn năm hàn thiết!"},
     "yeu_thu_drop": [5,6], "yt_drop_rate": 0.02, "yt_boss_rate": 0.05},
    # BC7 — Ngộ Đạo
    {"id": 7, "ten": "Bích Văn Động Thiên", "emoji": "📜",
     "mo_ta": "Động thiên khắc đầy bích văn thiên đạo. Ngộ Đạo tu sĩ giải mã chân lý của vũ trụ.",
     "cap_toi_thieu": 7,
     "phong_thuong": [
       {"ten": "Thiên Đạo Quỷ", "emoji": "📜", "hp": 505000, "at": 21650, "df": 2960, "hoi_tam": 5450, "bao_kich": 2.38, "ho_tam": 375, "khang_bao": 0.11, "exp_min": 10530, "exp_max": 17550, "lt_min": 8580, "lt_max": 12870, "nl_drop": [6, 7]},
       {"ten": "Cửu Vĩ Hồ",    "emoji": "🦊", "hp": 650000, "at": 27800, "df": 3820, "hoi_tam": 7000, "bao_kich": 2.55, "ho_tam": 473, "khang_bao": 0.12, "exp_min": 13500, "exp_max": 22500, "lt_min": 11000, "lt_max": 16500, "nl_drop": [6, 7]},
       {"ten": "Cổ Thần Nhân",  "emoji": "🗿", "hp": 813000, "at": 32500, "df": 4500, "hoi_tam": 8280, "bao_kich": 2.74, "ho_tam": 555, "khang_bao": 0.13, "exp_min": 16650, "exp_max": 27750, "lt_min": 13600, "lt_max": 20400, "nl_drop": [7, 8]}
       ],
     "boss": {"ten": "Khai Mệnh Thiên Hồ", "emoji": "🌸",
       "hp": 1050000, "at": 39000, "df": 4600, "hoi_tam": 12000, "bao_kich": 3.06, "ho_tam": 940, "khang_bao": 0.18,
       "exp_min": 22000, "exp_max": 36700, "lt_min": 20800, "lt_max": 31200, "nl_drop": [7,8],
       "mo_ta": "Khai Mệnh Thiên Hồ — chín đuôi rực sáng như thiên hà, một tiếng hú thay đổi mệnh trời!"},
     "yeu_thu_drop": [6,7], "yt_drop_rate": 0.015, "yt_boss_rate": 0.04},
    # BC8 — Vũ Hóa
    {"id": 8, "ten": "Hư Vô Địa Giới", "emoji": "🌌",
     "mo_ta": "Địa giới hư không giữa các cõi, không gian vỡ vụn. Vũ Hóa tu sĩ bước vào ranh giới của tồn tại.",
     "cap_toi_thieu": 8,
     "phong_thuong": [
       {"ten": "Hư Không Ảnh",  "emoji": "🌌", "hp": 592000, "at": 24800, "df": 3430, "hoi_tam": 6630, "bao_kich": 2.52, "ho_tam": 425, "khang_bao": 0.12, "exp_min": 20680, "exp_max": 34460, "lt_min": 18730, "lt_max": 28090, "nl_drop": [7, 8]},
       {"ten": "Linh Hầu",      "emoji": "🐒", "hp": 760000, "at": 31800, "df": 4430, "hoi_tam": 8500, "bao_kich": 2.70, "ho_tam": 533, "khang_bao": 0.13, "exp_min": 26500, "exp_max": 44200, "lt_min": 24000, "lt_max": 36000, "nl_drop": [7, 8]},
       {"ten": "Cổ Long Phách", "emoji": "🐲", "hp": 950000, "at": 37200, "df": 5230, "hoi_tam": 10070, "bao_kich": 2.92, "ho_tam": 625, "khang_bao": 0.14, "exp_min": 32760, "exp_max": 54600, "lt_min": 29640, "lt_max": 44460, "nl_drop": [8, 9]}
       ],
     "boss": {"ten": "Minh Xà", "emoji": "🐍",
       "hp": 1200000, "at": 44000, "df": 5300, "hoi_tam": 14000, "bao_kich": 3.24, "ho_tam": 1060, "khang_bao": 0.20,
       "exp_min": 43000, "exp_max": 71700, "lt_min": 44500, "lt_max": 66700, "nl_drop": [8,9],
       "mo_ta": "Minh Xà thần xà của cõi hư vô, thân dài vạn trượng bao trùm cả địa giới!"},
     "yeu_thu_drop": [7,8], "yt_drop_rate": 0.01, "yt_boss_rate": 0.03},
    # BC9 — Đăng Tiên
    {"id": 9, "ten": "Tháp Thực Hồn", "emoji": "🏯",
     "mo_ta": "Tháp cổ nuốt chửng hồn phách tu sĩ yếu đuối. Chỉ Đăng Tiên tu sĩ mới đủ sức chinh phục đỉnh tháp.",
     "cap_toi_thieu": 9,
     "phong_thuong": [
       {"ten": "Hồn Phách Quỷ",    "emoji": "💀", "hp": 678600, "at": 28860, "df": 3980, "hoi_tam": 7800, "bao_kich": 2.66, "ho_tam": 472, "khang_bao": 0.13, "exp_min": 57720, "exp_max": 96720,  "lt_min": 37450, "lt_max": 56170, "nl_drop": [8, 9]},
       {"ten": "Hỗn Độn Yêu Nhãn", "emoji": "👁️", "hp": 870000, "at": 37000, "df": 5130, "hoi_tam": 10000, "bao_kich": 2.85, "ho_tam": 593, "khang_bao": 0.14, "exp_min": 74000, "exp_max": 124000, "lt_min": 48000, "lt_max": 72000, "nl_drop": [8, 9]},
       {"ten": "Thực Hồn Tinh",     "emoji": "🌑", "hp": 1087500, "at": 43250, "df": 6100, "hoi_tam": 11850, "bao_kich": 3.07, "ho_tam": 695, "khang_bao": 0.15, "exp_min": 91400, "exp_max": 152900, "lt_min": 59260, "lt_max": 88880, "nl_drop": [9]}
       ],
     "boss": {"ten": "Hạn Bạt", "emoji": "☀️",
       "hp": 1400000, "at": 51200, "df": 6200, "hoi_tam": 17000, "bao_kich": 3.42, "ho_tam": 1180, "khang_bao": 0.21,
       "exp_min": 120000, "exp_max": 200000, "lt_min": 89000, "lt_max": 133000, "nl_drop": [9],
       "mo_ta": "Hạn Bạt — thần hạn thiêu đốt vạn linh, ngọn lửa của hắn có thể đốt cháy cả tiên giới!"},
     "yeu_thu_drop": [8,9], "yt_drop_rate": 0.01, "yt_boss_rate": 0.025},
]

BI_CANH_BY_ID = {bc["id"]: bc for bc in BI_CANH}
