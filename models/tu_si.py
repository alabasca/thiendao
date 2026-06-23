"""
TypedDict cho dữ liệu tu sĩ (ts) — dùng ở 50+ functions.
"""
from __future__ import annotations

from typing import TypedDict


class TuSiDict(TypedDict, total=False):
    user_id: int
    dao_hieu: str
    linh_can: int
    linh_can_phu: list[str]
    canh_gioi: int
    cap_nho: int
    exp: int
    hp: int
    hp_max: int
    cong: int
    thu: int
    linh_thach: int
    tong_mon: int
    phap_bao: list[int]
    phap_bao_active: int
    yeu_thu: list[int]
    yeu_thu_active: int
    sung_thu: dict[str, int]
    sung_thu_active: int
    dan_duoc: dict[str, int]
    nguyen_lieu: dict[str, int]
    thang_pvp: int
    thua_pvp: int
    ngay_tao: int
    cd_tu_luyen: int
    cd_dot_pha: int
    cd_khai_hoang: int
    cd_bi_canh: int
    cd_diem_danh: int
    chuoi_diem_danh: int
    tong_tu_luyen: int
    danh_hieu_hien: str
    gioi_tinh: str
    tuoi: int
    so_thich: str
    the_luc: int
    the_luc_cap_nhat: int
    tran_the_luc: int
    tran_the_luc_cap_nhat: int
    cong_phap_so_huu: list[int]
    cong_phap_trang_bi: dict[str, int]
    cong_phap_tang: dict[str, int]
    cong_phap_hoc: list[int]
    cong_phap_active: int
    bc_thua_lan_truoc: int
    tong_tu_vi: int
    linh_luc: int
    hoi_tam: int
    ho_tam: int
    bao_kich: int
    khang_bao: int
    banner_id: int
    the_chat: str
    linh_can_so_huu: list[str]
    linh_can_diem: dict[str, int]
    manh_linh_can: dict[str, int]
    linh_qua: dict[str, int]
    dotpha_tc_nl: dict[str, int]
    linh_can_lop2: dict[str, int]
    so_lan_trung_sinh: int
    ti_le_van_dinh: float
    van_dinh_all_stat_pct: float
    da_van_dinh: bool
    y_canh: dict
    tran_dao_active: str
    toa_ky: dict
    toa_ky_active: int
    toa_ky_herb: dict
    toa_ky_pity: int
    toa_ky_banner_featured_id: int
    toa_ky_banner_reset_ts: int
