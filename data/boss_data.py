from __future__ import annotations
from typing import Any

BOSS_THE_GIOI: list[dict[str, Any]] = [
    {"id": 0, "ten": "Hình Thiên", "emoji": "👹", "image_file": "images/hinhthien.jpg",
     "hp_max": 50_000_000, "canh_gioi_pool": [3, 4, 5, 6],
     "phan_thuong": {"nl": [2, 3], "yeu_thu": None}},
    {"id": 1, "ten": "Trường Thừa", "emoji": "👺", "image_file": "images/truongthua.jpg",
     "hp_max": 50_000_000, "canh_gioi_pool": [3, 4, 5, 6],
     "phan_thuong": {"nl": [3, 4], "yeu_thu": None}},
    {"id": 2, "ten": "Đào Ngột", "emoji": "🐲", "image_file": "images/thaothiet.jpg",
     "hp_max": 50_000_000, "canh_gioi_pool": [3, 4, 5, 6],
     "phan_thuong": {"nl": [3, 4, 5], "yeu_thu": 5}},
    {"id": 3, "ten": "Kế Mông", "emoji": "💀", "image_file": "images/kemong.png",
     "hp_max": 50_000_000, "canh_gioi_pool": [3, 4, 5, 6],
     "phan_thuong": {"nl": [4, 5], "yeu_thu": 6}},
    {"id": 4, "ten": "Thái Cổ Tiên Chủ", "emoji": "🪽", "image_file": "images/thaothiet.jpg",
     "hp_max": 6_000_000_000, "canh_gioi_pool": [9],
     "phan_thuong": {"nl": [5], "yeu_thu": 17}},
]

BOSS_SPAWN_HOURS_VN = [0, 6, 12, 18]
