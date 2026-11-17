import streamlit as st
import sxtwl
from datetime import datetime, timedelta, timezone, date, time
import ephem
import warnings
import re

warnings.filterwarnings('ignore')
st.set_page_config(page_title="Ngọa Long Kỳ Môn", layout="wide", initial_sidebar_state="collapsed")

# ==========================================
# 1. DỮ LIỆU CƠ BẢN & HẰNG SỐ CHÂN TRUYỀN
# ==========================================
thien_can = "甲乙丙丁戊己庚辛壬癸"
dia_chi = "子丑寅卯辰巳午未申酉戌亥"
luc_nghi = ["戊", "己", "庚", "辛", "壬", "癸", "丁", "丙", "乙"]

WOLONG_OUTER_PALACES = [4, 9, 2, 7, 6, 1, 8, 3] 
WOLONG_FLYING_PATH = [5, 6, 7, 8, 9, 1, 2, 3, 4] 
WOLONG_NUM_TO_STEM = {1: "癸", 2: "丁", 3: "丙", 4: "乙", 5: "戊", 6: "己", 7: "庚", 8: "辛", 9: "壬", 0: "甲"}
WOLONG_ORIGINAL_GATES = {1: "休门", 8: "生门", 3: "伤门", 4: "杜门", 9: "景门", 2: "死门", 7: "惊门", 6: "开门"}
WOLONG_CLOCKWISE_GATES = ["景门", "死门", "惊门", "开门", "休门", "生门", "伤门", "杜门"]

wolong_jq_order = ["大雪", "冬至", "小寒", "大寒", "立春", "雨水", "惊蛰", "春分", "清明", "谷雨", "立夏", "小满", "芒种", "夏至", "小暑", "大暑", "立秋", "处暑", "白露", "秋分", "寒露", "霜降", "立冬", "小雪"]

GATE_TO_TRIGRAM = {"休门": "地", "生门": "雷", "伤门": "火", "杜门": "泽", "景门": "天", "死门": "风", "惊门": "水", "开门": "山"}
TIEN_THIEN_MAP = {9: "天", 1: "地", 3: "火", 7: "水", 6: "山", 2: "风", 8: "雷", 4: "泽"}

# Hào từ dưới lên trên: (Hào 1, Hào 2, Hào 3) -> 1 là Dương, 0 là Âm
TRIGRAM_TO_BITS = {
    "天": (1, 1, 1),
    "泽": (1, 1, 0),
    "火": (1, 0, 1),
    "雷": (1, 0, 0),
    "风": (0, 1, 1),
    "水": (0, 1, 0),
    "山": (0, 0, 1),
    "地": (0, 0, 0),
}
BITS_TO_TRIGRAM = {v: k for k, v in TRIGRAM_TO_BITS.items()}

EVAL_DICT = {
    "风": {"泽":"〇", "天":"△", "风":"✕", "火":"〇", "水":"△", "雷":"〇", "地":"✕", "山":"〇"},
    "天": {"泽":"✕", "天":"△", "风":"✕", "火":"〇", "水":"✕", "雷":"△", "地":"✕", "山":"✕"},
    "水": {"泽":"✕", "天":"✕", "风":"✕", "火":"〇", "水":"✕", "雷":"✕", "地":"〇", "山":"✕"},
    "泽": {"泽":"△", "天":"✕", "风":"✕", "火":"✕", "水":"✕", "雷":"✕", "地":"〇", "山":"〇"},
    "山": {"泽":"△", "天":"〇", "风":"✕", "火":"✕", "水":"✕", "雷":"〇", "地":"✕", "山":"✕"},
    "火": {"泽":"✕", "天":"〇", "风":"〇", "火":"✕", "水":"✕", "雷":"△", "地":"〇", "山":"✕"},
    "地": {"泽":"〇", "天":"〇", "风":"〇", "火":"✕", "水":"✕", "雷":"〇", "地":"△", "山":"△"},
    "雷": {"泽":"✕", "天":"△", "风":"〇", "火":"〇", "水":"〇", "雷":"△", "地":"〇", "山":"✕"}
}

HEX_CHINESE_DICT = {
    ("天","天"): (1, "乾"), ("地","地"): (2, "坤"), ("水","雷"): (3, "屯"), ("山","水"): (4, "蒙"),
    ("水","天"): (5, "需"), ("天","水"): (6, "訟"), ("地","水"): (7, "師"), ("水","地"): (8, "比"),
    ("风","天"): (9, "小畜"), ("天","泽"): (10, "履"), ("地","天"): (11, "泰"), ("天","地"): (12, "否"),
    ("天","火"): (13, "同人"), ("火","天"): (14, "大有"), ("地","山"): (15, "謙"), ("雷","地"): (16, "豫"),
    ("泽","雷"): (17, "隨"), ("山","风"): (18, "蠱"), ("地","泽"): (19, "臨"), ("风","地"): (20, "觀"),
    ("火","雷"): (21, "噬嗑"), ("山","火"): (22, "賁"), ("山","地"): (23, "剝"), ("地","雷"): (24, "復"),
    ("天","雷"): (25, "無妄"), ("山","天"): (26, "大畜"), ("山","雷"): (27, "頤"), ("泽","风"): (28, "大過"),
    ("水","水"): (29, "坎"), ("火","火"): (30, "離"), ("泽","山"): (31, "咸"), ("雷","风"): (32, "恆"),
    ("天","山"): (33, "遯"), ("雷","天"): (34, "大壯"), ("火","地"): (35, "晉"), ("地","火"): (36, "明夷"),
    ("风","火"): (37, "家人"), ("火","泽"): (38, "睽"), ("水","山"): (39, "蹇"), ("雷","水"): (40, "解"),
    ("山","泽"): (41, "損"), ("风","雷"): (42, "益"), ("泽","天"): (43, "夬"), ("天","风"): (44, "姤"),
    ("泽","地"): (45, "萃"), ("地","风"): (46, "升"), ("泽","水"): (47, "困"), ("水","风"): (48, "井"),
    ("泽","火"): (49, "革"), ("火","风"): (50, "鼎"), ("雷","雷"): (51, "震"), ("山","山"): (52, "艮"),
    ("风","山"): (53, "漸"), ("雷","泽"): (54, "歸妹"), ("雷","火"): (55, "豐"), ("火","山"): (56, "旅"),
    ("风","风"): (57, "巽"), ("泽","泽"): (58, "兌"), ("风","水"): (59, "渙"), ("水","泽"): (60, "節"),
    ("风","泽"): (61, "中孚"), ("雷","山"): (62, "小過"), ("水","火"): (63, "既濟"), ("火","水"): (64, "未濟")
}

ORIGINAL_STARS = {1: "天蓬", 2: "天芮", 3: "天冲", 4: "天辅", 5: "天禽", 6: "天心", 7: "天柱", 8: "天任", 9: "天英"}
DEITIES = ["值符", "螣蛇", "太阴", "六合", "勾陈", "朱雀", "九地", "九天"] 

KIGAKU_OPPOSITE = {1: 9, 2: 8, 3: 7, 4: 6, 6: 4, 7: 3, 8: 2, 9: 1, 5: 5}
KIGAKU_HOME = {1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 6, 7: 7, 8: 8, 9: 9}
KIGAKU_COMPATIBILITY = {
    1: [3, 4, 6, 7], 2: [6, 7, 8, 9], 3: [1, 4, 9], 4: [1, 3, 9], 5: [2, 6, 7, 8, 9],
    6: [1, 2, 7, 8], 7: [1, 2, 6, 8], 8: [2, 6, 7, 9], 9: [2, 3, 4, 8]
}
BRANCH_TO_PALACE = {"子": 1, "丑": 8, "寅": 8, "卯": 3, "辰": 4, "巳": 4, "午": 9, "未": 2, "申": 2, "酉": 7, "戌": 6, "亥": 6}

# ==========================================
# 2. LOGIC LỊCH (NHẬT BÀN 360 NGÀY ÂM LỊCH)
# ==========================================
def get_xun_leader(can, chi):
    return {"子":"戊", "戌":"己", "申":"庚", "午":"辛", "辰":"壬", "寅":"癸"}[dia_chi[(dia_chi.index(chi) - thien_can.index(can)) % 12]]

def get_hour_nine_star(day_branch, hour_branch, dun_type):
    hb_idx = dia_chi.index(hour_branch) 
    start_star = 1 if day_branch in ["子","午","卯","酉"] else (4 if day_branch in ["辰","戌","丑","未"] else 7)
    if dun_type == "阴遁": start_star = 7 if day_branch in ["辰","戌","丑","未"] else (4 if day_branch in ["寅","申","巳","亥"] else 1)
    res = (start_star + hb_idx) % 9 if dun_type == "阳遁" else (start_star - hb_idx) % 9
    return 9 if res == 0 else res

def calculate_correct_ju(nguyen, can_gio, chi_gio, tiet_khi):
    base_ju_dict = {"夏至":9,"小暑":7,"大暑":6,"立秋":5,"处暑":6,"白露":5,"秋分":4,"寒露":9,"霜降":8,"立冬":7,"小雪":2,"大雪":1,"冬至":1,"小寒":3,"大寒":4,"立春":5,"雨水":4,"惊蛰":5,"春分":6,"清明":1,"谷雨":2,"立夏":3,"小满":8,"芒种":9}
    yin_dun_terms = ["夏至", "小暑", "大暑", "立秋", "处暑", "白露", "秋分", "寒露", "霜降", "立冬", "小雪", "大雪"]
    dun_type = -1 if tiet_khi in yin_dun_terms else 1
    tuan_index = ((thien_can.index(can_gio) - dia_chi.index(chi_gio)) % 12) // 2
    nguyen_multiplier = 0 if nguyen == "上" else 1 if nguyen == "中" else 2
    raw_ju = base_ju_dict[tiet_khi] + (dun_type * (tuan_index + 6 * nguyen_multiplier))
    return (raw_ju - 1) % 9 + 1

def get_wushu_dun(day_stem, hour_branch):
    return thien_can[((thien_can.index(day_stem) % 5) * 2 + dia_chi.index(hour_branch)) % 10]

def get_custom_lunar_day_data(solar_date):
    """ 360 NGÀY ÂM LỊCH TÍNH CẢ TIẾT KHÍ """
    day_obj = sxtwl.fromSolar(solar_date.year, solar_date.month, solar_date.day)
    l_month = day_obj.getLunarMonth()
    l_day = day_obj.getLunarDay()
    is_leap = day_obj.isLunarLeap()
    
    L = (l_month - 1) * 30 + l_day
    
    if 136 <= L <= 315:
        dun_type = "阴遁"
        offset = L - 136
        star = 9 - (offset % 9)
        if star == 0: star = 9
    else:
        dun_type = "阳遁"
        offset = L - 316 if L >= 316 else 44 + L 
        star = (offset % 9) + 1
        
    can = thien_can[offset % 10]
    chi = dia_chi[offset % 12]
    
    # --- TÍNH TIẾT KHÍ & TAM NGUYÊN (TOÁN HỌC) ---
    abs_day = ((l_month - 11) % 12) * 30 + (l_day - 1)
    wl_jieqi = wolong_jq_order[abs_day // 15 % 24]
    day_in_jq = abs_day % 15
    wl_yuan = "上" if day_in_jq < 5 else "中" if day_in_jq < 10 else "下"
    
    return l_month, l_day, is_leap, can, chi, dun_type, star, wl_jieqi, wl_yuan

def get_menh_cung(b_day_star, b_hour_star):
    """Đặt sao giờ sinh vào trung cung bay thuận, tìm vị trí sao ngày sinh ra Mệnh Cung"""
    idx = (b_day_star - b_hour_star) % 9
    return WOLONG_FLYING_PATH[idx]

# ================= LOGIC LỤC DIỆU & NGŨ ĐỘN =================

def get_tdn_data(lunar_month, lunar_day, chi_gio_idx, is_leap=False):
    # 1. TÍNH NGŨ ĐỘN
    ss_base_ch = ['贵人', '印财', '退财', '五鬼', '阳虎', '阴虎']
    hour_num = chi_gio_idx + 1
    base_month = (lunar_month - 2) % 6
    e1_day = (base_month + lunar_day) % 6
    e2_hour = (e1_day + hour_num) % 6
    e3_month = (e2_hour + lunar_month) % 6
    e4_day = (e3_month + lunar_day) % 6
    e5_hour = (e4_day + hour_num) % 6
    
    raw_ss = [ss_base_ch[e1_day], ss_base_ch[e2_hour], ss_base_ch[e3_month], ss_base_ch[e4_day], ss_base_ch[e5_hour]]
    has_yin, has_gui, has_tui = '印财' in raw_ss, '贵人' in raw_ss, '退财' in raw_ss
    can_transform = (has_yin or has_gui) and not has_tui
    
    final_ss = []
    count_qui_nhan = 0
    count_ngu_quy = 0
    
    for ss in raw_ss:
        if ss == '阳虎' and can_transform: final_ss.append('正官')
        elif ss == '阴虎' and can_transform: final_ss.append('副官')
        elif ss == '退财': final_ss.append("<span style='color:#000000;'>退财</span>") 
        else: 
            final_ss.append(ss)
            if ss == '贵人': count_qui_nhan += 1
            if ss == '五鬼': count_ngu_quy += 1

    ss_set = set(re.sub(r"<[^>]+>", "", item) for item in final_ss) # Dọn HTML để check logic
    
    # LUẬT ĐÁNH GIÁ
    wd_status = "XẤU" 
    
    if '退财' in ss_set: 
        if '贵人' in ss_set and '五鬼' not in ss_set: wd_status = "平"
    else:
        if '印财' in ss_set:
            wd_status = "吉"
        elif '五鬼' in ss_set and '贵人' in ss_set and count_qui_nhan >= count_ngu_quy:
            wd_status = "平"

    # 2. TÍNH LỤC DIỆU
    calc_month = lunar_month
    if is_leap:
        if lunar_day >= 16:
            calc_month = lunar_month + 1
            if calc_month > 12: calc_month = 1

    idx_month = (calc_month - 1) % 6
    idx_day = (idx_month + lunar_day - 1) % 6
    idx_hour = (idx_day + hour_num - 1) % 6
    
    names = ['大安', '留连', '速喜', '赤口', '小吉', '空亡']
    elements = ['木', '土', '火', '金', '水', '土']
    
    def get_luc_than(khach_idx, ta_idx):
        e_khach, e_ta = elements[khach_idx], elements[ta_idx]
        if e_khach == e_ta: return '兄弟'
        sinh = {'木':'火', '火':'土', '土':'金', '金':'水', '水':'木'}
        khac = {'木':'土', '土':'水', '水':'火', '火':'金', '金':'木'}
        if sinh[e_khach] == e_ta: return '父母'
        if sinh[e_ta] == e_khach: return '子孙'
        if khac[e_khach] == e_ta: return '官鬼'
        if khac[e_ta] == e_khach: return '妻财'

    str_thang_html = f"{get_luc_than(idx_month, idx_hour)} - {names[idx_month]}"
    str_ngay_html  = f"{get_luc_than(idx_day, idx_hour)} - {names[idx_day]}"
    str_gio_html   = f"{names[idx_hour]}"
    final_liu_yao_html = f"{str_thang_html}<br>{str_ngay_html}<br>{str_gio_html}"
    
    str_thang_text = f"{names[idx_month]} ({get_luc_than(idx_month, idx_hour)})"
    str_ngay_text  = f"{names[idx_day]} ({get_luc_than(idx_day, idx_hour)})"
    str_gio_text   = f"{names[idx_hour]}"
    final_liu_yao_text = f"[{str_thang_text}, {str_ngay_text}, {str_gio_text}]"
        
    return final_ss, final_liu_yao_html, str_gio_text, final_liu_yao_text, wd_status

# ==========================================
# 3. LẬP BÀN TOÁN HỌC 
# ==========================================
def lap_que_wolong(can_ngay, chi_ngay, dun_type, ju_num, daily_star):
    cung_data = {i: {'dia': '', 'mon': '', 'thien': '', 'sao': '', 'than': '', 'day_star': ''} for i in range(1, 10)}
    
    current_val = (10 - ju_num) if dun_type == "阳遁" else ju_num
    step_dir = 1 if dun_type == "阳遁" else -1
    dia_ban = {}
    for cung in WOLONG_FLYING_PATH:
        can = WOLONG_NUM_TO_STEM.get(current_val, "")
        dia_ban[cung] = can
        cung_data[cung]['dia'] = can
        current_val += step_dir
        if current_val > 9: current_val = 1
        elif current_val < 1: current_val = 9

    luc_nghi_ngay = get_xun_leader(can_ngay, chi_ngay)
    p_circle_list = [c for c, can in dia_ban.items() if can == luc_nghi_ngay] 
    p_circle = p_circle_list[0] if p_circle_list else 5

    target_stem = luc_nghi_ngay if can_ngay == '甲' else can_ngay
    p_day_stem_list = [c for c, can in dia_ban.items() if can == target_stem]
    p_day_stem = p_day_stem_list[0] if p_day_stem_list else 5

    # LẬP THIÊN BÀN CAN
    if p_circle == 5:
        for i in WOLONG_OUTER_PALACES: cung_data[i]['thien'] = dia_ban[i]
        cung_data[5]['thien'] = dia_ban[p_day_stem]
        cung_data[p_day_stem]['thien'] = dia_ban[5]
    elif p_day_stem == 5:
        for i in WOLONG_OUTER_PALACES: cung_data[i]['thien'] = dia_ban[i] 
        cung_data[5]['thien'] = dia_ban[5] 
    else:
        idx_source = WOLONG_OUTER_PALACES.index(p_circle)
        idx_target = WOLONG_OUTER_PALACES.index(p_day_stem)
        offset = (idx_target - idx_source) % 8
        for i in range(8):
            cung_data[WOLONG_OUTER_PALACES[i]]['thien'] = dia_ban[WOLONG_OUTER_PALACES[(i - offset) % 8]]
        cung_data[5]['thien'] = dia_ban[5]

    # LẬP BÁT MÔN
    s_steps = thien_can.index(can_ngay)
    seq = [1, 2, 3, 4, 5, 6, 7, 8, 9] if dun_type == "阳遁" else [9, 8, 7, 6, 5, 4, 3, 2, 1]
    p_land = seq[(seq.index(p_circle) + s_steps) % 9]

    if p_circle == 5 or s_steps == 0 or p_land == 5:
        for p, door in WOLONG_ORIGINAL_GATES.items(): cung_data[p]['mon'] = door
    else:
        g_start = WOLONG_ORIGINAL_GATES[p_circle]
        idx_land = WOLONG_OUTER_PALACES.index(p_land)
        idx_gate = WOLONG_CLOCKWISE_GATES.index(g_start)
        for i in range(8):
            cung_data[WOLONG_OUTER_PALACES[(idx_land + i) % 8]]['mon'] = WOLONG_CLOCKWISE_GATES[(idx_gate + i) % 8]

    # LẬP CỬU TINH
    curr_star = daily_star 
    for cung in WOLONG_FLYING_PATH:
        cung_data[cung]['day_star'] = curr_star
        curr_star = 1 if curr_star == 9 else curr_star + 1

    luoshu_9 = [1, 2, 3, 4, 5, 6, 7, 8, 9]
    idx_base_star = luoshu_9.index(p_circle)
    idx_target_star = luoshu_9.index(p_day_stem)
    shift_for_star = (idx_target_star - idx_base_star) % 9
    for i in range(1, 10):
        idx_new = (luoshu_9.index(i) + shift_for_star) % 9
        cung_data[luoshu_9[idx_new]]['sao'] = ORIGINAL_STARS[i]
    cung_data[5]['sao'] = ""

    anchor_palace = p_day_stem
    if anchor_palace == 5: anchor_palace = 8 if dun_type == "阳遁" else 7

    idx_anchor = WOLONG_OUTER_PALACES.index(anchor_palace)
    for i in range(8):
        if dun_type == "阳遁": cung_data[WOLONG_OUTER_PALACES[(idx_anchor + i) % 8]]['than'] = DEITIES[i]
        else: cung_data[WOLONG_OUTER_PALACES[(idx_anchor - i) % 8]]['than'] = DEITIES[i]
    cung_data[5]['than'] = ""

    cung_phi_tinh = cung_data[5]['day_star']
    return cung_data, p_circle, cung_phi_tinh, p_land

# ==========================================
# 4. MODULE PHÂN TÍCH CAN - MÔN - QUẺ DỊCH
# ==========================================
def analyze_wolong_board(cung_data, can_tuan):
    can_can_data = {
        '甲':{'甲':'吉','乙':'凶','丙':'吉','丁':'吉','戊':'凶','己':'吉','庚':'大凶','辛':'凶','壬':'凶','癸':'吉'},
        '乙':{'甲':'吉','乙':'凶','丙':'吉','丁':'吉','戊':'吉','己':'吉','庚':'凶','辛':'大凶','壬':'吉','癸':'凶'},
        '丙':{'甲':'吉','乙':'吉','丙':'凶','丁':'吉','戊':'吉','己':'吉','庚':'大凶','辛':'吉','壬':'吉','癸':'凶'},
        '丁':{'甲':'吉','乙':'吉','丙':'吉','丁':'吉','戊':'吉','己':'凶','庚':'吉','辛':'凶','壬':'吉','癸':'大凶'},
        '戊':{'甲':'凶','乙':'吉','丙':'吉','丁':'吉','戊':'凶','己':'凶','庚':'凶','辛':'凶','壬':'吉','癸':'凶'},
        '己':{'甲':'凶','乙':'吉','丙':'凶','丁':'凶','戊':'吉','己':'凶','庚':'凶','辛':'凶','壬':'凶','癸':'凶'},
        '庚':{'甲':'大凶','乙':'凶','丙':'大凶','丁':'吉','戊':'凶','己':'大凶','庚':'大凶','辛':'凶','壬':'大凶','癸':'大凶'},
        '辛':{'甲':'凶','乙':'大凶','丙':'凶','丁':'吉','戊':'凶','己':'凶','庚':'凶','辛':'凶','壬':'凶','癸':'凶'},
        '壬':{'甲':'凶','乙':'凶','丙':'凶','丁':'吉','戊':'吉','己':'凶','庚':'凶','辛':'吉','壬':'凶','癸':'凶'},
        '癸':{'甲':'吉','乙':'凶','丙':'吉','丁':'大凶','戊':'吉','己':'凶','庚':'大凶','辛':'凶','壬':'凶','癸':'凶'}
    }
    cat_mon = {"休门", "生门", "景门", "开门"}

    stem_colors = {i: "#000000" for i in range(1, 10)}
    mon_colors = {i: "#000000" for i in range(1, 10)}

    for p in range(1, 10):
        if p == 5 or p not in cung_data: continue

        t_can = '甲' if cung_data[p]['thien'] == can_tuan else cung_data[p]['thien']
        d_can = '甲' if cung_data[p]['dia'] == can_tuan else cung_data[p]['dia']
        if t_can in can_can_data and d_can in can_can_data[t_can]:
            eval_res = can_can_data[t_can][d_can]
            stem_colors[p] = "#000000" if "凶" in eval_res else "#CC0000"

        mon_colors[p] = "#CC0000" if cung_data[p]['mon'] in cat_mon else "#000000"

    return stem_colors, mon_colors

def calculate_center_hexagram(cung_data, menh_cung, p_circle, sel_hour, sel_minute):
    """
    Tính Quẻ Dịch cuối cùng ở Trung Cung cho Thời Bàn:
    - Thượng Quái: Bát Môn tại Mệnh Cung
    - Hạ Quái: Bát Môn tại vị trí Tuần Thủ Giáp trên Địa Bàn (p_circle)
    - Biến Hào: Chia 120 phút của canh giờ thành 6 khoảng 20 phút (Hào 1 -> Hào 6)
    - Nếu menh_cung == 5 hoặc p_circle == 5: trả về None (không hiển thị quẻ)
    """
    if menh_cung == 5 or p_circle == 5:
        return None

    upper_gate = cung_data[menh_cung]['mon']
    lower_gate = cung_data[p_circle]['mon']
    if not upper_gate or not lower_gate:
        return None

    upper_tri = GATE_TO_TRIGRAM.get(upper_gate)
    lower_tri = GATE_TO_TRIGRAM.get(lower_gate)
    if not upper_tri or not lower_tri:
        return None

    minutes_in_branch = sel_minute if sel_hour % 2 == 1 else (60 + sel_minute)
    hao_idx = minutes_in_branch // 20  # 0..5 (Hào 1 -> Hào 6)

    bits = list(TRIGRAM_TO_BITS[lower_tri] + TRIGRAM_TO_BITS[upper_tri])
    bits[hao_idx] = 1 - bits[hao_idx]

    final_lower_tri = BITS_TO_TRIGRAM[tuple(bits[:3])]
    final_upper_tri = BITS_TO_TRIGRAM[tuple(bits[3:])]

    hex_num, hex_name = HEX_CHINESE_DICT[(final_upper_tri, final_lower_tri)]
    eval_sym = EVAL_DICT[final_upper_tri][final_lower_tri]
    eval_color_map = {"〇": "#CC0000", "△": "#D4AF37", "✕": "#000000"}

    return {
        'num': hex_num,
        'name': hex_name,
        'eval': eval_sym,
        'color': eval_color_map[eval_sym]
    }

def evaluate_kigaku_formations(birth_star, current_stars, breaker_branch, mode="日家"):
    k_data = {i: {'stars': {}, 'honmei': False} for i in range(1, 10)}
    
    cung_ngu_hoang_d = [p for p, s in current_stars.items() if s == 5][0]
    cung_ban_menh_d = [p for p, s in current_stars.items() if s == birth_star][0]
    
    for p in range(1, 10):
        s_val = current_stars[p]
        is_bad = False
        
        if p != 5: 
            if p == cung_ban_menh_d: 
                k_data[p]['honmei'] = True
                is_bad = True
            if cung_ban_menh_d != 5 and p == KIGAKU_OPPOSITE[cung_ban_menh_d]: 
                is_bad = True
            if p == cung_ngu_hoang_d: 
                is_bad = True
            if cung_ngu_hoang_d != 5 and p == KIGAKU_OPPOSITE[cung_ngu_hoang_d]: 
                is_bad = True
            if p == KIGAKU_OPPOSITE[BRANCH_TO_PALACE[breaker_branch]]: 
                is_bad = True  

        if s_val == 5 or is_bad:
            color = "#000000"
        else:
            color = "#CC0000"
            
        k_data[p]['stars']['d'] = (s_val, color) 
            
    return k_data

# ==========================================
# 5. GIAO DIỆN HTML RENDER
# ==========================================
def render_html_table(cung_data, center_hex, stem_colors, mon_colors, can_tuan, kigaku_data, tdn_data=None, loai_ban="日家"):
    luoi_lac_thu = [[4, 9, 2], [3, 5, 7], [8, 1, 6]]
    
    tbl_w, tbl_h = "100%", "100%"
    f_can = "6.0cqw"       
    f_k_star = "4.5cqw"    
    f_form = "2.4cqw"  
        
    html = f"""
    <style>
        * {{ box-sizing: border-box; }}
        body {{ margin: 0; padding: 0; }}
        .responsive-container {{ width: 100%; margin: 0 auto; container-type: inline-size; display: flex; justify-content: center; }}
        .qmdj-wrapper {{ width: 100%; aspect-ratio: 1 / 1; position: relative; font-family: sans-serif; display: flex; justify-content: center; align-items: center; }}
        .qmdj-table {{ border-collapse: collapse; width: {tbl_w}; height: {tbl_h}; table-layout: fixed; background: #fff; z-index: 2; }}
        .qmdj-td {{ border: 1px solid #aaa; width: 33.33%; position: relative; vertical-align: top; padding: 1.5cqw; }}
        
        .top-right-panel {{ position: absolute; top: 1cqw; right: 1.5cqw; display: flex; flex-direction: row-reverse; gap: 1cqw; align-items: flex-start;}}
        .formation-item {{ display: flex; flex-direction: column; align-items: center; justify-content: flex-start; font-weight: bold; color: #000; font-size: 3.5cqw;}}
        
        .bottom-left-stems {{ position: absolute; bottom: 1.5cqw; left: 1.5cqw; display: flex; flex-direction: column; align-items: center; gap: 0.5cqw; }}
        
        .bottom-right-godgate {{ position: absolute; bottom: 1.5cqw; right: 1.5cqw; display: flex; flex-direction: column; align-items: center; gap: 0.5cqw; font-size: {f_can}; font-weight: bold; line-height: 1; }}
        
        .kigaku-col {{ position: absolute; top: 1cqw; left: 1cqw; display: flex; flex-direction: column; }}
        .k-row {{ display: flex; flex-direction: row; align-items: flex-start; gap: 1cqw;}}
        .k-star {{ font-size: {f_k_star}; font-weight: bold; width: 3cqw; text-align: center; line-height: 1;}}
    </style>

    <div class="responsive-container">
        <div class="qmdj-wrapper">
    """

    html += '<table class="qmdj-table">'
    for row in luoi_lac_thu:
        html += "<tr>"
        for p in row:
            d = cung_data[p]
            k_d = kigaku_data[p]
            
            t_can, d_can = d.get('thien', ''), d.get('dia', '')
            base_color = stem_colors.get(p, "#000000") 
            t_decor = "underline" if t_can == can_tuan else "none"
            d_decor = "underline" if d_can == can_tuan else "none"
            
            t_style = f"font-weight: bold; color: {base_color}; font-size: {f_can}; text-decoration: {t_decor}; text-underline-offset: 3px; text-decoration-thickness: 2px; line-height: 1;"
            d_style = f"font-weight: bold; color: {base_color}; font-size: {f_can}; text-decoration: {d_decor}; text-underline-offset: 3px; text-decoration-thickness: 2px; line-height: 1;"

            mon_km = d.get('mon', '')
            mon_col = mon_colors.get(p, "#000000")

            ds_val, ds_col = k_d['stars']['d']
            ds_decor = "underline" if k_d.get('honmei') else "none"
            kigaku_html = f'<div class="kigaku-col"><div class="k-row"><div class="k-star" style="color:{ds_col}; text-decoration:{ds_decor}; text-decoration-color:#000000; text-underline-offset:3px; text-decoration-thickness:2px;">{ds_val}</div></div></div>'
            stems_html = f'<div class="bottom-left-stems"><div style="{t_style}">{t_can}</div><div style="{d_style}">{d_can}</div></div>'

            if p == 5:
                wudun_html = ""
                center_hex_html = ""
                if loai_ban == "时家":
                    if center_hex:
                        vert_hex = "<br>".join(list(center_hex['name']))
                        center_hex_html = (
                            f"<div class='top-right-panel'>"
                            f"<div class='formation-item' style='color:{center_hex['color']};'>"
                            f"<div style='text-align: center; line-height: 1.15;'>{vert_hex}"
                            f"<div style='font-size: 0.8em; font-weight: normal; color: #666; margin-top: 3px;'>({center_hex['num']})</div>"
                            f"</div></div></div>"
                        )
                    if tdn_data:
                        final_ss, _, _, _, _ = tdn_data
                        wudun_html = f"<div style='position: absolute; bottom: 1.5cqw; right: 1.5cqw; color: #666666; font-size: {f_form}; text-align: right; line-height: 1.4; font-weight: bold;'>{'<br>'.join(final_ss)}</div>"
                    
                html += f'<td class="qmdj-td">{kigaku_html}{center_hex_html}{stems_html}{wudun_html}</td>'
            else:
                than_km = d.get('than', '')
                godgate_html = f'<div class="bottom-right-godgate"><div style="color:#666666;">{than_km}</div><div style="color:{mon_col};">{mon_km}</div></div>'
                html += f'<td class="qmdj-td">{kigaku_html}{stems_html}{godgate_html}</td>'
        html += "</tr>"
    html += "</table></div></div>"
    return html

# ==========================================
# 6. STREAMLIT APP MAIN
# ==========================================
def get_current_vn_time(): return datetime.now(timezone(timedelta(hours=7)))
if "init_dt" not in st.session_state: st.session_state.init_dt = get_current_vn_time()

col1, col2, col3, col4, col5, col6, col7, col8 = st.columns([1, 0.7, 0.7, 1, 0.7, 0.7, 0.8, 0.8])

with col1: selected_date = st.date_input("Ngày Xem", value=st.session_state.init_dt.date(), min_value=date(1901, 1, 1), max_value=date(2100, 12, 31))
with col2: selected_hour = st.selectbox("Giờ Xem", options=list(range(24)), index=st.session_state.init_dt.hour)
with col3: selected_minute = st.selectbox("Phút Xem", options=list(range(60)), index=st.session_state.init_dt.minute)
with col4: birth_date = st.date_input("Ngày Sinh", value=date(1993, 1, 7), min_value=date(1901, 1, 1), max_value=date(2100, 12, 31))
with col5: birth_hour = st.selectbox("Giờ Sinh", options=list(range(24)), index=8)
with col6: birth_minute = st.selectbox("Phút Sinh", options=list(range(60)), index=15)
with col7: selected_tz = st.selectbox("Múi Giờ", options=list(range(-12, 15)), index=19, format_func=lambda x: f"UTC{'+' if x>=0 else ''}{x}")
with col8: loai_ban = st.selectbox("Loại Bàn", options=["日家", "时家"], index=1)

# --- TÍNH TOÁN SAO BẢN MỆNH & MỆNH CUNG ---
actual_birth_date = birth_date + timedelta(days=1) if birth_hour >= 23 else birth_date

# 1. Lấy thông tin Lịch của Ngày Sinh
_, _, _, b_can_ngay, b_chi_ngay, b_dun, b_day_star, _, _ = get_custom_lunar_day_data(actual_birth_date)

# 2. Tính Chi Giờ Sinh
b_chi_gio_idx = 0 if birth_hour >= 23 else (birth_hour + 1) // 2 % 12
b_chi_gio = dia_chi[b_chi_gio_idx]

# 3. Tính Sao Giờ Sinh (Theo Âm/Dương Độn thực tế của ngày sinh)
b_hour_star = get_hour_nine_star(b_chi_ngay, b_chi_gio, b_dun)

# 4. Gán Sao Bản Mệnh & Tính Mệnh Cung
user_birth_star = b_day_star if loai_ban == "日家" else b_hour_star
user_menh_cung = get_menh_cung(b_day_star, b_hour_star)

hoa_giap_60 = [thien_can[i%10] + dia_chi[i%12] for i in range(60)]
cuc_so_list = [f"阳遁{i}局" for i in range(1, 10)] + [f"阴遁{i}局" for i in range(1, 10)]

st.markdown("<div style='height: 5px;'></div>", unsafe_allow_html=True)

_, col_opt1, col_opt2, col_opt3, _ = st.columns([1.5, 2, 2, 2, 1.5])
with col_opt1: manual_hoagiap = st.selectbox("Hoa Giáp", options=["Tùy Chọn"] + hoa_giap_60)
with col_opt2: manual_cucso = st.selectbox("Cục Số", options=["Tùy Chọn"] + cuc_so_list)
with col_opt3: manual_cuutinh = st.selectbox("Cửu Tinh", options=["Tùy Chọn"] + [str(i) for i in range(1, 10)])

user_dt = datetime.combine(selected_date, time(selected_hour, selected_minute))
actual_date = user_dt.date() + timedelta(days=1) if user_dt.hour >= 23 else user_dt.date()

# 1. Tính toán gốc
l_month, l_day, is_leap, can_ngay_str, chi_ngay_str, base_dun, base_ju, wl_jieqi, wl_yuan = get_custom_lunar_day_data(actual_date)
ngay_can_chi = can_ngay_str + chi_ngay_str

chi_gio_idx = 0 if user_dt.hour >= 23 else (user_dt.hour + 1) // 2 % 12
chi_gio_str = dia_chi[chi_gio_idx]
can_gio_str = get_wushu_dun(can_ngay_str, chi_gio_str)

# 2. Phân nhánh dữ liệu theo Loại Bàn
if loai_ban == "日家":
    wl_can = can_ngay_str
    wl_chi = chi_ngay_str
    wl_dun = base_dun
    wl_ju = base_ju
    actual_daily_star = base_ju
    is_nhuan_period = is_leap 
else:
    wl_can = can_gio_str
    wl_chi = chi_gio_str
    wl_dun = base_dun
    wl_ju = calculate_correct_ju(wl_yuan, wl_can, wl_chi, wl_jieqi)
    actual_daily_star = get_hour_nine_star(chi_ngay_str, wl_chi, wl_dun)
    is_nhuan_period = False

# 3. GHI ĐÈ DỮ LIỆU TỪ MENU LỰA CHỌN
if manual_hoagiap != "Tùy Chọn":
    wl_can = manual_hoagiap[0]
    wl_chi = manual_hoagiap[1]
    if loai_ban == "日家": 
        ngay_can_chi = manual_hoagiap

if manual_cucso != "Tùy Chọn":
    wl_dun = "阳遁" if "阳" in manual_cucso else "阴遁"
    wl_ju = int(manual_cucso.replace("阳遁", "").replace("阴遁", "").replace("局", ""))

if manual_cuutinh != "Tùy Chọn":
    actual_daily_star = int(manual_cuutinh) 

# 4. TẠO TIÊU ĐỀ SAU KHI ĐÃ GHI ĐÈ
if loai_ban == "日家":
    title_color = "#D4AF37" if is_nhuan_period else "#555" 
    font_weight = "bold" if is_nhuan_period else "normal"
    nhuan_str = "Nhuận " if is_nhuan_period else ""
    sub_title = f"<h4 style='margin-top:0px; margin-bottom:15px; font-family:sans-serif; color: {title_color}; font-weight: {font_weight}; font-size: 16px; text-align: center;'>阴历: {nhuan_str}{l_day}/{l_month} | {ngay_can_chi}日 | {wl_jieqi} {wl_yuan}元 | {wl_dun}{wl_ju}局</h4>"
else:
    sub_title = f"<h4 style='margin-top:0px; margin-bottom:15px; font-family:sans-serif; color: #555; font-weight: normal; font-size: 16px; text-align: center;'>阴历: {l_day}/{l_month} | {ngay_can_chi}日 {wl_can}{wl_chi}时 | {wl_jieqi} {wl_yuan}元 | {wl_dun}{wl_ju}局</h4>"

# 5. LẬP BÀN VÀ PHÂN TÍCH
data, p_circle, cung_phi_tinh, p_land = lap_que_wolong(wl_can, wl_chi, wl_dun, wl_ju, actual_daily_star)

can_tuan = get_xun_leader(wl_can, wl_chi)
stem_colors, mon_colors = analyze_wolong_board(data, can_tuan)
title = ""

# Tính Quẻ Dịch ở Trung Cung (chỉ cho Thời Bàn)
center_hex = None
if loai_ban == "时家":
    center_hex = calculate_center_hexagram(data, user_menh_cung, p_circle, selected_hour, selected_minute)

# 6. KHÍ HỌC
cung_day_stars = {p: data[p]['day_star'] for p in range(1, 10)}
breaker_chi = wl_chi 
kigaku_data = evaluate_kigaku_formations(user_birth_star, cung_day_stars, breaker_chi, loai_ban)

# 7. LỤC DIỆU, NGŨ ĐỘN (Vẫn tính toán, chỉ hiển thị Ngũ Độn ở Trung Cung)
tdn_data = None
if loai_ban == "时家":
    tdn_data = get_tdn_data(l_month, l_day, chi_gio_idx, is_leap)
    
qimen_board_html = render_html_table(data, center_hex, stem_colors, mon_colors, can_tuan, kigaku_data, tdn_data, loai_ban)

combined_html = f"""
<div style="width: 100%; max-width: 450px; margin: 0 auto; display: flex; flex-direction: column; align-items: center; justify-content: center; padding-top: 10px;">
    {title}{sub_title}{qimen_board_html}
</div>
"""
st.components.v1.html(combined_html, height=540, scrolling=False)


# ==========================================
# 7. MODULE SCAN: DỤNG SỰ
# ==========================================
st.markdown("---")
st.markdown("<h3 style='text-align: center; color: #333; font-family: sans-serif; margin-bottom: 20px;'>DỤNG SỰ</h3>", unsafe_allow_html=True)

huong_list = {"": None, "坎 (345 - 15)": 1, "艮 (15 - 75)": 8, "震 (75 - 105)": 3, "巽 (105 - 165)": 4, "離 (165 - 195)": 9, "坤 (195 - 255)": 2, "兌 (255 - 285)": 7, "乾 (285 - 345)": 6}

can_list = ["", "甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
mon_list = ["", "休门", "生门", "伤门", "杜门", "景门", "死门", "惊门", "开门"]

with st.container():
    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
    
    # HÀNG 1: Hướng -> Giờ -> Thiên Bàn -> Địa Bàn -> Bát Môn
    _, c1, c_gio, c2, c3, c4, _ = st.columns([0.1, 1, 1, 1, 1, 1, 0.1])
    loc_huong = c1.selectbox("方向 (Hướng)", options=list(huong_list.keys()))
    loc_gio = c_gio.selectbox("时辰 (Giờ)", options=[""] + list(dia_chi), disabled=(loai_ban=="日家"))
    loc_thien_can = c2.selectbox("天盤 (Thiên Bàn)", options=can_list)
    loc_dia_can = c3.selectbox("地盤 (Địa Bàn)", options=can_list)
    loc_mon = c4.selectbox("八门 (Bát Môn)", options=mon_list)
    
    # HÀNG 2: Thiên Thời -> Nhân Hòa -> Cát Nhật -> Ngũ Độn (Bỏ Lục Diệu)
    _, c11, c12, c13, c15, _ = st.columns([0.1, 1, 1, 1, 1, 0.1])
    loc_thien_thoi = c11.selectbox("天时 (Thiên Thời)", options=["", "天地干", "天地干 + 八门"])
    loc_nhan_hoa = c12.selectbox("人和 (Nhân Hòa)", options=["", "吉"])
    
    options_thoi = ["", "吉"] if loai_ban == "时家" else [""]
    options_ngu_don = ["", "吉", "平"] if loai_ban == "时家" else [""] 
    
    loc_cat_nhat = c13.selectbox("吉日 (Cát Nhật)", options=options_thoi, disabled=(loai_ban=="日家"))
    loc_ngu_don = c15.selectbox("五遁 (Ngũ Độn)", options=options_ngu_don, disabled=(loai_ban=="日家"))

if st.button("TÌM KIẾM", use_container_width=True):
    with st.spinner('Đang quét dữ liệu tương lai...'):
        results = []
        max_limit = 365 if loai_ban == "日家" else 1080 
        
        if loai_ban == "时家":
            if user_dt.hour % 2 == 0: current_scan_dt = (user_dt - timedelta(hours=1)).replace(minute=0, second=0)
            else: current_scan_dt = user_dt.replace(minute=0, second=0)
            current_scan_dt -= timedelta(hours=2) 
        else:
            current_scan_dt = datetime.combine(selected_date, time(selected_hour, selected_minute))
        
        loops = 0
        while loops < max_limit: 
            if len(results) >= 10: break 
            
            loops += 1
            wd_status = ""
            wd_text_in_ra = ""
            
            if loai_ban == "日家":
                current_scan_dt += timedelta(days=1)
                s_date = current_scan_dt.date() + timedelta(days=1) if current_scan_dt.hour >= 23 else current_scan_dt.date()
                _, _, _, can_ngay_scan, chi_ngay_scan, wl_dun_s, day_star_s, _, wl_yuan_s = get_custom_lunar_day_data(s_date)
                
                wl_ju_s = day_star_s
                scan_data, p_circle_scan, cung_phi_tinh_scan, p_land_scan = lap_que_wolong(can_ngay_scan, chi_ngay_scan, wl_dun_s, wl_ju_s, day_star_s)
                can_tuan_scan = get_xun_leader(can_ngay_scan, chi_ngay_scan)
                
                time_str = f"{s_date.strftime('%d/%m/%Y')}"
                c_str = f"{wl_dun_s} {wl_ju_s}局 | Ngày {can_ngay_scan}{chi_ngay_scan}"
                
            else:
                current_scan_dt += timedelta(hours=2) 
                s_date = current_scan_dt.date() + timedelta(days=1) if current_scan_dt.hour >= 23 else current_scan_dt.date()
                l_month_s, l_day_s, is_leap_s, can_ngay_scan, chi_ngay_scan, wl_dun_s, day_star_s, wl_jieqi_s, wl_yuan_s = get_custom_lunar_day_data(s_date)
                
                chi_gio_idx = 0 if current_scan_dt.hour >= 23 else (current_scan_dt.hour + 1) // 2 % 12
                chi_gio_scan = dia_chi[chi_gio_idx]
                
                final_ss_scan, _, _, _, wd_status = get_tdn_data(l_month_s, l_day_s, chi_gio_idx, is_leap_s)
                wd_text_in_ra = " ".join(final_ss_scan)
                
                if loc_gio and chi_gio_scan != loc_gio: continue
                if loc_ngu_don == "吉" and wd_status != "吉": continue
                if loc_ngu_don == "平" and wd_status not in ("吉", "平"): continue
                    
                can_gio_scan = get_wushu_dun(can_ngay_scan, chi_gio_scan)
                wl_ju_s = calculate_correct_ju(wl_yuan_s, can_gio_scan, chi_gio_scan, wl_jieqi_s)
                daily_star_scan = get_hour_nine_star(chi_ngay_scan, chi_gio_scan, wl_dun_s)
                
                scan_data, p_circle_scan, cung_phi_tinh_scan, p_land_scan = lap_que_wolong(can_gio_scan, chi_gio_scan, wl_dun_s, wl_ju_s, daily_star_scan)
                can_tuan_scan = get_xun_leader(can_gio_scan, chi_gio_scan)
                
                time_str = f"{current_scan_dt.strftime('%d/%m/%Y')} {current_scan_dt.strftime('%H:%M')}"
                c_str = f"Ngày {can_ngay_scan}{chi_ngay_scan} {can_gio_scan}{chi_gio_scan}时 | {wl_dun_s}{wl_ju_s}局"

            stem_colors_scan, mon_colors_scan = analyze_wolong_board(scan_data, can_tuan_scan)
            cung_day_stars_scan = {p: scan_data[p]['day_star'] for p in range(1, 10)}
            breaker_chi_scan = chi_ngay_scan if loai_ban == "日家" else chi_gio_scan
            kigaku_data_scan = evaluate_kigaku_formations(user_birth_star, cung_day_stars_scan, breaker_chi_scan, loai_ban)

            # ========================================================
            # 1. LẬP NHẬT BÀN NGẦM (Chạy khi có yêu cầu lọc Cát Nhật)
            # ========================================================
            day_stem_colors_scan = {}
            day_mon_colors_scan = {}
            day_kigaku_scan = {}
            if loai_ban == "时家" and loc_cat_nhat == "吉":
                day_wl_ju = day_star_s
                day_scan_data, _, _, _ = lap_que_wolong(can_ngay_scan, chi_ngay_scan, wl_dun_s, day_wl_ju, day_star_s)
                day_can_tuan_leader = get_xun_leader(can_ngay_scan, chi_ngay_scan)
                day_stem_colors_scan, day_mon_colors_scan = analyze_wolong_board(day_scan_data, day_can_tuan_leader)
                
                day_cung_day_stars = {p: day_scan_data[p]['day_star'] for p in range(1, 10)}
                day_kigaku_scan = evaluate_kigaku_formations(b_day_star, day_cung_day_stars, chi_ngay_scan, "日家")
            # ========================================================

            target_palace = huong_list[loc_huong] 

            def check_match(p):
                d = scan_data[p]
                t_chk = '甲' if d['thien'] == can_tuan_scan else d['thien']
                d_chk = '甲' if d['dia'] == can_tuan_scan else d['dia']
                
                # 1. Lọc Cơ bản
                if loc_thien_can and t_chk != loc_thien_can: return False
                if loc_dia_can and d_chk != loc_dia_can: return False
                if loc_mon and d['mon'] != loc_mon: return False
                    
                # 2. LỌC THIÊN THỜI
                if loc_thien_thoi == "天地干":
                    if stem_colors_scan.get(p, "#000000") == "#000000": return False
                elif loc_thien_thoi == "天地干 + 八门":
                    if stem_colors_scan.get(p, "#000000") == "#000000": return False
                    if mon_colors_scan.get(p, "#000000") == "#000000": return False
                    
                # 3. LỌC NHÂN HÒA
                if loc_nhan_hoa == "吉":
                    _, current_k_col = kigaku_data_scan[p]['stars']['d']
                    if current_k_col == "#000000": return False

                # 4. LỌC CÁT NHẬT (Thiên Địa Can cát + Nhân Hòa cát + Bát Môn cát)
                if loai_ban == "时家" and loc_cat_nhat == "吉":
                    if day_stem_colors_scan.get(p, "#000000") == "#000000": return False
                    if day_mon_colors_scan.get(p, "#000000") == "#000000": return False
                    _, day_k_col = day_kigaku_scan[p]['stars']['d']
                    if day_k_col == "#000000": return False

                return True

            is_match = False
            
            if target_palace:
                if target_palace != 5: 
                    is_match = check_match(target_palace)
            else:
                for p in range(1, 10):
                    if p == 5: continue
                    is_match = check_match(p)
                    if is_match:
                        target_palace = p
                        break
                        
            if is_match:
                ten_cung = [k for k, v in huong_list.items() if v == target_palace][0]
                
                res_mon = scan_data[target_palace]['mon']
                res_mon_col = mon_colors_scan.get(target_palace, "#000000")
                res_than = scan_data[target_palace]['than']
                res_thien = scan_data[target_palace]['thien']
                res_dia = scan_data[target_palace]['dia']
                res_stem_col = stem_colors_scan.get(target_palace, "#000000")
                res_stems_html = f"<span style='color:{res_stem_col}; font-weight:bold;'>{res_thien}</span>/<span style='color:{res_stem_col}; font-weight:bold;'>{res_dia}</span>"

                d_star_val, d_star_col = kigaku_data_scan[target_palace]['stars']['d']
                d_decor = "underline" if kigaku_data_scan[target_palace].get('honmei') else "none"
                d_style = f"color:{d_star_col}; font-weight:bold; font-size:16px; text-decoration:{d_decor}; text-decoration-color:#000000; text-underline-offset:2px; text-decoration-thickness:2px;"
                kigaku_result_html = f" | Cửu Tinh: <span style='{d_style}'>{d_star_val}</span>"
                
                day_board_html = ""
                if loai_ban == "时家":
                    day_wl_ju = day_star_s
                    day_scan_data, _, _, _ = lap_que_wolong(can_ngay_scan, chi_ngay_scan, wl_dun_s, day_wl_ju, day_star_s)
                    day_can_tuan = get_xun_leader(can_ngay_scan, chi_ngay_scan)
                    
                    day_stem_colors, day_mon_colors = analyze_wolong_board(day_scan_data, day_can_tuan)
                    
                    day_cung_day_stars = {p: day_scan_data[p]['day_star'] for p in range(1, 10)}
                    day_kigaku = evaluate_kigaku_formations(b_day_star, day_cung_day_stars, chi_ngay_scan, "日家")
                    
                    d_mon = day_scan_data[target_palace]['mon']
                    d_than = day_scan_data[target_palace]['than']
                    d_thien = day_scan_data[target_palace]['thien']
                    d_dia = day_scan_data[target_palace]['dia']
                    
                    d_mon_col = day_mon_colors.get(target_palace, "#000000")
                    d_stem_col = day_stem_colors.get(target_palace, "#000000")

                    d_star_val2, d_star_col2 = day_kigaku[target_palace]['stars']['d']
                    d_decor2 = "underline" if day_kigaku[target_palace].get('honmei') else "none"
                    d_style2 = f"color:{d_star_col2}; font-weight:bold; font-size:16px; text-decoration:{d_decor2}; text-decoration-color:#000000; text-underline-offset:2px; text-decoration-thickness:2px;"
                    kigaku_day_html = f" | Cửu Tinh: <span style='{d_style2}'>{d_star_val2}</span>"
                    
                    day_stems_html = f"<span style='color:{d_stem_col}; font-weight:bold;'>{d_thien}</span>/<span style='color:{d_stem_col}; font-weight:bold;'>{d_dia}</span>"
                    day_board_html = f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;↳ <b>[Nhật Bàn]</b> | {day_stems_html} | <span style='color:{d_mon_col}; font-weight:bold;'>{d_mon}</span> | <span style='color:#666666; font-weight:bold;'>{d_than}</span>{kigaku_day_html}"

                results.append((time_str, c_str, ten_cung, kigaku_result_html, res_mon, res_mon_col, res_than, day_board_html, res_stems_html, wd_text_in_ra))

        if results:
            st.success(f"**TÌM THẤY {len(results)} KẾT QUẢ:**")
            for idx, (t_str, canchi_str, cung_str, kigaku_html, m_name, m_col, t_than, day_board_html, stems_html, wd_text_in_ra) in enumerate(results):
                h_text = f" | Hướng: {cung_str}" if cung_str else ""
                mon_html = f" | <span style='color:{m_col}; font-weight:bold;'>{m_name}</span>"
                than_html = f" | <span style='color:#666666; font-weight:bold;'>{t_than}</span>" if t_than else ""
                wd_html = f" | <span style='color:#666666; font-weight:bold;'>{wd_text_in_ra}</span>" if wd_text_in_ra else ""
                
                if loai_ban == "时家":
                    st.markdown(f"{idx+1}. {t_str}{h_text} | {stems_html}{mon_html}{than_html}{kigaku_html}{wd_html}", unsafe_allow_html=True)
                else:
                    st.markdown(f"{idx+1}. {t_str} | {canchi_str}{h_text} | {stems_html}{mon_html}{than_html}{kigaku_html}", unsafe_allow_html=True)
                if day_board_html:
                    st.markdown(day_board_html, unsafe_allow_html=True)
                st.markdown("<div style='height: 5px;'></div>", unsafe_allow_html=True)
        else:
            st.warning("Không tìm thấy ngày nào thỏa mãn TẤT CẢ các điều kiện trong 1 năm tới.")
