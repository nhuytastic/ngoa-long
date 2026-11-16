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

ORIGINAL_STARS = {1: "天蓬", 2: "天芮", 3: "天冲", 4: "天辅", 5: "天禽", 6: "天心", 7: "天柱", 8: "天任", 9: "天英"}
DEITIES = ["值符", "螣蛇", "太阴", "六合", "勾陈", "朱雀", "九地", "九天"] 

wolong_jq_order = ["大雪", "冬至", "小寒", "大寒", "立春", "雨水", "惊蛰", "春分", "清明", "谷雨", "立夏", "小满", "芒种", "夏至", "小暑", "大暑", "立秋", "处暑", "白露", "秋分", "寒露", "霜降", "立冬", "小雪"]

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
        cung_data[5]['thien'] = dia_ban[5] 
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
    
    # BÍ TRUYỀN: Nếu Tuần Thủ ở Trung Cung, ép quỹ đạo bay thuận. Còn lại bay theo Âm/Dương.
    if p_circle == 5:
        seq = [1, 2, 3, 4, 5, 6, 7, 8, 9] 
    else:
        seq = [1, 2, 3, 4, 5, 6, 7, 8, 9] if dun_type == "阳遁" else [9, 8, 7, 6, 5, 4, 3, 2, 1]
        
    p_land = seq[(seq.index(p_circle) + s_steps) % 9]

    # 1. Xác định Trực Sử
    if p_circle == 5:
        g_start = "死门" 
    else:
        g_start = WOLONG_ORIGINAL_GATES[p_circle]

    # 2. Rải Bát Môn
    if s_steps == 0 or p_land == 5: 
        # Khóa Phục Ngâm khi ngày Giáp hoặc bay trúng Trung Cung
        for p, door in WOLONG_ORIGINAL_GATES.items(): cung_data[p]['mon'] = door
    else:
        # Rải thuận kim đồng hồ vòng ngoài
        idx_land = WOLONG_OUTER_PALACES.index(p_land)
        idx_gate = WOLONG_CLOCKWISE_GATES.index(g_start)
        for i in range(8):
            cung_data[WOLONG_OUTER_PALACES[(idx_land + i) % 8]]['mon'] = WOLONG_CLOCKWISE_GATES[(idx_gate + i) % 8]

    #cung_data[5]['mon'] = "杜门" if dun_type == "阳遁" else "开门"

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

    # LẬP BÁT THẦN
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
# 4. MODULE PHÂN TÍCH CÁCH CỤC
# ==========================================
def qimen_analyzer_hojo(cung_data, can_tuan, p_land):
    cung_status = {i: [] for i in range(1, 10)}
    can_can_data = {'甲':{'甲':'吉','乙':'凶','丙':'吉','丁':'吉','戊':'凶','己':'吉','庚':'大凶','辛':'凶','壬':'凶','癸':'吉'}, '乙':{'甲':'吉','乙':'凶','丙':'吉','丁':'吉','戊':'吉','己':'吉','庚':'凶','辛':'大凶','壬':'吉','癸':'凶'}, '丙':{'甲':'吉','乙':'吉','丙':'凶','丁':'吉','戊':'吉','己':'吉','庚':'大凶','辛':'吉','壬':'吉','癸':'凶'}, '丁':{'甲':'吉','乙':'吉','丙':'吉','丁':'吉','戊':'吉','己':'凶','庚':'吉','辛':'凶','壬':'吉','癸':'大凶'}, '戊':{'甲':'凶','乙':'吉','丙':'吉','丁':'吉','戊':'凶','己':'凶','庚':'凶','辛':'凶','壬':'吉','癸':'凶'}, '己':{'甲':'凶','乙':'吉','丙':'凶','丁':'凶','戊':'吉','己':'凶','庚':'凶','辛':'凶','壬':'凶','癸':'凶'}, '庚':{'甲':'大凶','乙':'凶','丙':'大凶','丁':'吉','戊':'凶','己':'大凶','庚':'大凶','辛':'凶','壬':'大凶','癸':'大凶'}, '辛':{'甲':'凶','乙':'大凶','丙':'凶','丁':'吉','戊':'凶','己':'凶','庚':'凶','辛':'凶','壬':'凶','癸':'凶'}, '壬':{'甲':'凶','乙':'凶','丙':'凶','丁':'吉','戊':'吉','己':'凶','庚':'凶','辛':'吉','壬':'凶','癸':'凶'}, '癸':{'甲':'吉','乙':'凶','丙':'吉','丁':'大凶','戊':'吉','己':'凶','庚':'大凶','辛':'凶','壬':'凶','癸':'凶'}}

    def get_actual(can): return '甲' if can == can_tuan else can

    for p, d in cung_data.items():
        if p == 5: continue 
        raw_t, raw_d = d['thien'], d['dia']
        if not raw_t or not raw_d: continue

        t_can, d_can = get_actual(raw_t), get_actual(raw_d)
        mon, sao, than = d['mon'], d['sao'], d['than']

        if t_can == '甲' and d_can == '丙': cung_status[p].append(("青龙返首", "#CC0000"))
        if t_can == '丙' and d_can == '甲': cung_status[p].append(("飛鳥跌穴", "#CC0000"))
        if t_can == '丁' and p == p_land: cung_status[p].append(("玉女守門", "#CC0000"))
        if t_can == '乙' and p == 3: cung_status[p].append(("乙奇昇殿", "#CC0000"))
        if t_can == '丙' and p == 9: cung_status[p].append(("丙奇昇殿", "#CC0000"))
        if t_can == '丁' and p == 7: cung_status[p].append(("丁奇昇殿", "#CC0000")) 
        if t_can == '乙' and d_can == '己': cung_status[p].append(("乙奇得使", "#CC0000"))
        if t_can == '丙' and d_can == '戊': cung_status[p].append(("丙奇得使", "#CC0000"))
        if t_can == '丁' and d_can == '壬': cung_status[p].append(("丁奇得使", "#CC0000"))
        
        if t_can == '丙' and d_can == '戊' and mon == "生门": cung_status[p].append(("天遁", "#CC0000"))
        if t_can == '乙' and d_can == '己' and mon == "开门": cung_status[p].append(("地遁", "#CC0000"))
        if t_can == '丁' and mon == "休门" and than == "太阴": cung_status[p].append(("人遁", "#CC0000"))
        if t_can == '丙' and mon == "生门" and than == "九天": cung_status[p].append(("神遁", "#CC0000"))
        if t_can == '丁' and mon == "开门" and than == "九地": cung_status[p].append(("鬼遁", "#CC0000"))
        if (t_can == '乙' and mon == "开门") or (t_can == '乙' and p == 6 and mon in ["休门", "生门"]): cung_status[p].append(("龙遁", "#CC0000"))
        if (t_can == '乙' and mon == "生门") or (t_can == '乙' and p == 8 and mon in ["休门", "开门"]): cung_status[p].append(("虎遁", "#CC0000"))
        if t_can == '乙' and p == 4 and mon in ["休门", "生门", "开门"]: cung_status[p].append(("風遁", "#CC0000"))
        if t_can == '乙' and p == 2 and mon in ["休门", "生门", "开门"]: cung_status[p].append(("雲遁", "#CC0000"))

        if (t_can == '己' and p == 2) or (t_can == '辛' and p == 9) or (t_can == '壬' and p == 4) or (t_can == '癸' and p == 4) or (t_can == '戊' and p == 3) or (t_can == '庚' and p == 8): cung_status[p].append(("六儀撃刑", "#000000"))
        if t_can == '乙' and p == 2: cung_status[p].append(("乙奇入墓", "#000000"))
        if t_can == '丙' and p == 6: cung_status[p].append(("丙奇入墓", "#000000"))
        if t_can == '丁' and p == 6: cung_status[p].append(("丁奇入墓", "#000000"))
        
        if t_can == '庚' and d_can == '癸': cung_status[p].append(("大格", "#000000"))
        if t_can == '庚' and d_can == '壬': cung_status[p].append(("小格", "#000000"))
        if t_can == '庚' and d_can == '己': cung_status[p].append(("刑格", "#000000"))
        if t_can == '庚' and d_can == '庚': cung_status[p].append(("戰格", "#000000"))
        if t_can == '庚' and d_can == '甲': cung_status[p].append(("伏宮格", "#000000"))
        if t_can == '甲' and d_can == '庚': cung_status[p].append(("飛宮格", "#000000"))
        if t_can == '乙' and d_can == '辛': cung_status[p].append(("青龙逃走", "#000000"))
        if t_can == '辛' and d_can == '乙': cung_status[p].append(("白虎猖狂", "#000000"))
        if t_can == '丙' and d_can == '庚': cung_status[p].append(("熒惑入白", "#000000"))
        if t_can == '庚' and d_can == '丙': cung_status[p].append(("太白入熒", "#000000"))
        if t_can == '丁' and d_can == '癸': cung_status[p].append(("朱雀投江", "#000000"))
        if t_can == '癸' and d_can == '丁': cung_status[p].append(("螣蛇妖嬌", "#000000"))

        if (mon == "休门" and p == 9) or (mon == "景门" and p == 7) or (mon == "生门" and p == 1) or (mon == "开门" and p == 3): cung_status[p].append(("八門受制", "#000000"))
        if t_can == d_can and t_can not in ['甲', '丁']: cung_status[p].append(("干伏吟", "#000000"))
        if (t_can, d_can) in [('戊','辛'), ('辛','戊'), ('己','壬'), ('壬','己'), ('庚','癸'), ('癸','庚')]: cung_status[p].append(("干反吟", "#000000"))

        sao_mon_goc = {"天蓬":"休门", "天芮":"死门", "天冲":"伤门", "天辅":"杜门", "天心":"开门", "天柱":"惊门", "天任":"生门", "天英":"景门"}
        mon_doi_xung = {"休门":"景门", "死门":"生门", "伤门":"惊门", "杜门":"开门", "开门":"杜门", "惊门":"伤门", "生门":"死门", "景门":"休门"}
        if sao in sao_mon_goc:
            if mon == sao_mon_goc[sao]: cung_status[p].append(("星門伏吟", "#000000"))
            elif mon == mon_doi_xung[sao_mon_goc[sao]]: cung_status[p].append(("星門反吟", "#000000"))

    # LOGIC MÀU ĐỎ/ĐEN CỦA THẦN - MÔN
    tinh_mon_cat = {"天蓬": ["生门", "开门"], "天芮": ["休门", "景门", "开门"], "天冲": ["休门", "生门", "景门", "开门"], "天辅": ["休门", "生门", "景门"], "天禽": [], "天心": ["休门", "生门", "景门", "开门"], "天柱": ["休门", "生门", "景门", "开门"], "天任": ["休门", "景门", "开门"], "天英": ["生门", "开门"]}
    than_cat_chung = ["值符", "太阴", "六合", "九地", "九天"]

    stem_colors, mon_colors, than_colors = {i: "#000000" for i in range(1, 10)}, {i: "#000000" for i in range(1, 10)}, {i: "#000000" for i in range(1, 10)}
    
    for p in range(1, 10):
        if p == 5 or p not in cung_data: continue
        
        t_can = '甲' if cung_data[p]['thien'] == can_tuan else cung_data[p]['thien']
        d_can = '甲' if cung_data[p]['dia'] == can_tuan else cung_data[p]['dia']
        if t_can in can_can_data and d_can in can_can_data[t_can]:
            eval_res = can_can_data[t_can][d_can]
            stem_colors[p] = "#000000" if "凶" in eval_res else "#CC0000"
            
        sao_hien_tai, mon_hien_tai = cung_data[p]['sao'], cung_data[p]['mon']
        if sao_hien_tai in tinh_mon_cat and mon_hien_tai in tinh_mon_cat[sao_hien_tai]: mon_colors[p] = "#CC0000" 
        else: mon_colors[p] = "#000000" 
            
        than_hien_tai, phi_tinh_ngay = cung_data[p]['than'], cung_data[p]['day_star'] 
        if phi_tinh_ngay != 5 and than_hien_tai in than_cat_chung: than_colors[p] = "#CC0000"
        else: than_colors[p] = "#000000"

    for p in cung_status:
        formatted_list = []
        for raw_name, color in cung_status[p]:
            vert_text = "<br>".join(list(raw_name))
            display_name = f"<div style='text-align: center; line-height: 1.15;'>{vert_text}</div>"
            formatted_list.append((display_name, color))
        cung_status[p] = formatted_list

    return cung_status, stem_colors, mon_colors, than_colors

def evaluate_kigaku_formations(birth_star, current_stars, breaker_branch, mode="日家"):
    k_data = {i: {'stars': {}, 'honmei': False} for i in range(1, 10)}
    
    cung_ngu_hoang_d = [p for p, s in current_stars.items() if s == 5][0]
    cung_ban_menh_d = [p for p, s in current_stars.items() if s == birth_star][0]
    
    for p in range(1, 10):
        s_val = current_stars[p]
        is_bad = False # Cờ đánh dấu xem cung này có Hung tinh không
        
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
def render_html_table(cung_data, cung_status, stem_colors, mon_colors, than_colors, can_tuan, kigaku_data, tdn_data=None, loai_ban="日家"):
    luoi_lac_thu = [[4, 9, 2], [3, 5, 7], [8, 1, 6]]
    
    tbl_w, tbl_h = "100%", "100%"
    f_can = "5.5cqw"       
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
        .formation-item {{ display: flex; flex-direction: column; align-items: center; justify-content: flex-start; font-weight: bold; color: #000; font-size: {f_form};}}
        
        .bottom-left-stems {{ position: absolute; bottom: 1.5cqw; left: 1.5cqw; display: flex; flex-direction: column; align-items: center; gap: 0.5cqw; }}
        
        .bottom-right-godgate {{ position: absolute; bottom: 1.5cqw; right: 1.5cqw; display: flex; flex-direction: column; align-items: center; gap: 0.5cqw; font-size: {f_can}; font-weight: bold; line-height: 1; }}
        
        .kigaku-col {{ position: absolute; top: 1cqw; left: 1cqw; display: flex; flex-direction: column; }}
        .k-row {{ display: flex; flex-direction: row; align-items: flex-start; gap: 1cqw;}}
        
        .k-star {{ font-size: {f_k_star}; font-weight: bold; width: 3cqw; text-align: center; line-height: 1;}}
        .k-forms {{ display: flex; flex-direction: row; gap: 0.5cqw; font-weight: bold; font-size: {f_form};}}
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

            than_km = d.get('than', '')
            mon_km = d.get('mon', '')
            than_col = than_colors.get(p, "#000000")
            mon_col = mon_colors.get(p, "#000000")

            ds_val, ds_col = k_d['stars']['d']
            ds_decor = "underline" if k_d.get('honmei') else "none"
            kigaku_html = f'<div class="kigaku-col"><div class="k-row"><div class="k-star" style="color:{ds_col}; text-decoration:{ds_decor}; text-decoration-color:#000000; text-underline-offset:3px; text-decoration-thickness:2px;">{ds_val}</div></div></div>'
            stems_html = f'<div class="bottom-left-stems"><div style="{t_style}">{t_can}</div><div style="{d_style}">{d_can}</div></div>'

            if p == 5:
                wudun_html = ""
                liuyao_html = ""
                if loai_ban == "时家" and tdn_data:
                    final_ss, final_liu_yao_html, _, _, _ = tdn_data
                    
                    liuyao_html = f"<div style='position: absolute; top: 1cqw; right: 1.5cqw; color: #666666; font-size: {f_form}; text-align: right; line-height: 1.6; font-weight: bold;'>{final_liu_yao_html}</div>"

                    wudun_html = f"<div style='position: absolute; bottom: 1.5cqw; right: 1.5cqw; color: #666666; font-size: {f_form}; text-align: right; line-height: 1.4; font-weight: bold;'>{'<br>'.join(final_ss)}</div>"
                    
                html += f'<td class="qmdj-td">{kigaku_html}{stems_html}{liuyao_html}{wudun_html}</td>'
            else:
                godgate_html = f'<div class="bottom-right-godgate"><div style="color:{than_col};">{than_km}</div><div style="color:{mon_col};">{mon_km}</div></div>'
                form_html = "".join([f"<div class='formation-item' style='color:{f_color};'>{f_name}</div>" for f_name, f_color in cung_status[p]])
                html += f'<td class="qmdj-td">{kigaku_html}<div class="top-right-panel">{form_html}</div>{stems_html}{godgate_html}</td>'
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

# --- TÍNH TOÁN SAO BẢN MỆNH LINH HOẠT THEO LOẠI BÀN ---
# 1. Lấy thông tin Lịch của Ngày Sinh
_, _, _, b_can_ngay, b_chi_ngay, b_dun, b_day_star, _, _ = get_custom_lunar_day_data(birth_date)

# 2. Tính Chi Giờ Sinh
b_chi_gio_idx = 0 if birth_hour >= 23 else (birth_hour + 1) // 2 % 12
b_chi_gio = dia_chi[b_chi_gio_idx]

# 3. Tính Sao Giờ Sinh (Theo đúng công thức Thời Bàn)
b_hour_star = get_hour_nine_star(b_chi_ngay, b_chi_gio, b_dun)

# 4. Gán Sao Bản Mệnh
user_birth_star = b_day_star if loai_ban == "日家" else b_hour_star

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

# 3. GHI ĐÈ DỮ LIỆU TỪ MENU LỰA CHỌN (Phải đặt ở đây trước khi tạo Tiêu đề)
if manual_hoagiap != "Tùy Chọn":
    wl_can = manual_hoagiap[0]
    wl_chi = manual_hoagiap[1]
    if loai_ban == "日家": 
        ngay_can_chi = manual_hoagiap # Đổi Can Chi ngày trên tiêu đề

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
cung_st, stem_colors, mon_colors, than_colors = qimen_analyzer_hojo(data, can_tuan, p_land)
title = ""

# 6. KHÍ HỌC
cung_day_stars = {p: data[p]['day_star'] for p in range(1, 10)}
# Biến breaker_chi lấy trực tiếp wl_chi để tự động theo Hoa giáp ghi đè
breaker_chi = wl_chi 
kigaku_data = evaluate_kigaku_formations(user_birth_star, cung_day_stars, breaker_chi, loai_ban)

# 7. LỤC DIỆU, NGŨ ĐỘN
tdn_data = None
if loai_ban == "时家":
    tdn_data = get_tdn_data(l_month, l_day, chi_gio_idx, is_leap)
    
qimen_board_html = render_html_table(data, cung_st, stem_colors, mon_colors, than_colors, can_tuan, kigaku_data, tdn_data, loai_ban)

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
tinh_list = ["", "天蓬", "天芮", "天冲", "天辅", "天禽", "天心", "天柱", "天任", "天英"]
than_list = ["", "值符", "螣蛇", "太阴", "六合", "勾陈", "朱雀", "九地", "九天"]
cat_cach_list = ["", "天遁", "地遁", "人遁", "神遁", "鬼遁", "青竜返首", "飛鳥跌穴", "玉女守門", "竜遁", "虎遁", "風遁", "雲遁", "乙奇昇殿", "丙奇昇殿", "丁奇昇殿"]

with st.container():
    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
    
    # HÀNG 1: Hướng -> Giờ -> Thiên Bàn -> Địa Bàn -> Bát Môn -> Bát Thần -> Cát Cách
    _, c1, c_gio, c2, c3, c4, c5, c6, _ = st.columns([0.1, 1, 1, 1, 1, 1, 1, 1, 0.1])
    loc_huong = c1.selectbox("方向 (Hướng)", options=list(huong_list.keys()))
    loc_gio = c_gio.selectbox("时辰 (Giờ)", options=[""] + list(dia_chi), disabled=(loai_ban=="日家"))
    loc_thien_can = c2.selectbox("天盤 (Thiên Bàn)", options=can_list)
    loc_dia_can = c3.selectbox("地盤 (Địa Bàn)", options=can_list)
    loc_mon = c4.selectbox("八门 (Bát Môn)", options=mon_list)
    loc_than = c5.selectbox("八神 (Bát Thần)", options=than_list)
    loc_cat_cach = c6.selectbox("吉格 (Cát Cách)", options=cat_cach_list)
    
    # HÀNG 2: Thiên Thời -> Nhân Hòa -> Cát Nhật -> Lục Diệu -> Ngũ Độn
    _, c11, c12, c13, c14, c15, _ = st.columns([0.1, 1, 1, 1, 1, 1, 0.1])
    loc_thien_thoi = c11.selectbox("天时 (Thiên Thời)", options=["", "天地干", "吉"])
    loc_nhan_hoa = c12.selectbox("人和 (Nhân Hòa)", options=["", "吉"])
    
    options_thoi = ["", "吉"] if loai_ban == "时家" else [""]
    options_luc_dieu = ["", "大安", "留连", "速喜", "赤口", "小吉", "空亡"] if loai_ban == "时家" else [""]
    options_ngu_don = ["", "吉", "平"] if loai_ban == "时家" else [""] 
    
    loc_cat_nhat = c13.selectbox("吉日 (Cát Nhật)", options=options_thoi, disabled=(loai_ban=="日家"))
    loc_luc_dieu = c14.selectbox("六曜 (Lục Diệu)", options=options_luc_dieu, disabled=(loai_ban=="日家"))
    loc_ngu_don = c15.selectbox("五遁 (Ngũ Độn)", options=options_ngu_don, disabled=(loai_ban=="日家"))

import re 

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
            ly_text_in_ra = ""
            gio_ly = ""
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
                
                final_ss_scan, _, gio_ly, ly_text_in_ra, wd_status = get_tdn_data(l_month_s, l_day_s, chi_gio_idx, is_leap_s)
                wd_text_in_ra = " ".join(final_ss_scan)
                
                if loc_gio and chi_gio_scan != loc_gio: continue
                if loc_luc_dieu and gio_ly != loc_luc_dieu: continue
                if loc_ngu_don == "吉" and wd_status != "吉": continue
                if loc_ngu_don == "平" and wd_status not in ("吉", "平"): continue
                    
                can_gio_scan = get_wushu_dun(can_ngay_scan, chi_gio_scan)
                wl_ju_s = calculate_correct_ju(wl_yuan_s, can_gio_scan, chi_gio_scan, wl_jieqi_s)
                daily_star_scan = get_hour_nine_star(chi_ngay_scan, chi_gio_scan, wl_dun_s)
                
                scan_data, p_circle_scan, cung_phi_tinh_scan, p_land_scan = lap_que_wolong(can_gio_scan, chi_gio_scan, wl_dun_s, wl_ju_s, daily_star_scan)
                can_tuan_scan = get_xun_leader(can_gio_scan, chi_gio_scan)
                
                time_str = f"{current_scan_dt.strftime('%d/%m/%Y')} {current_scan_dt.strftime('%H:%M')}"
                c_str = f"Ngày {can_ngay_scan}{chi_ngay_scan} {can_gio_scan}{chi_gio_scan}时 | {wl_dun_s}{wl_ju_s}局"

            cung_st_scan, stem_colors_scan, mon_colors_scan, than_colors_scan = qimen_analyzer_hojo(scan_data, can_tuan_scan, p_land_scan)
            cung_day_stars_scan = {p: scan_data[p]['day_star'] for p in range(1, 10)}
            breaker_chi_scan = chi_ngay_scan if loai_ban == "日家" else chi_gio_scan
            kigaku_data_scan = evaluate_kigaku_formations(user_birth_star, cung_day_stars_scan, breaker_chi_scan, loai_ban)
            val_cat_cach = loc_cat_cach

            # ========================================================
            # 1. LẬP NHẬT BÀN NGẦM (Chạy khi có yêu cầu lọc Cát Nhật)
            # ========================================================
            day_stem_colors_scan = {}
            day_mon_colors_scan = {}
            day_than_colors_scan = {}
            day_kigaku_scan = {}
            if loai_ban == "时家" and loc_cat_nhat == "吉":
                day_wl_ju = day_star_s
                day_scan_data, day_can_tuan, _, day_p_land = lap_que_wolong(can_ngay_scan, chi_ngay_scan, wl_dun_s, day_wl_ju, day_star_s)
                day_can_tuan_leader = get_xun_leader(can_ngay_scan, chi_ngay_scan)
                _, day_stem_colors_scan, day_mon_colors_scan, day_than_colors_scan = qimen_analyzer_hojo(day_scan_data, day_can_tuan_leader, day_p_land)
                
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
                if loc_than and d['than'] != loc_than: return False
                
                # 2. Lọc Cát Cách
                if val_cat_cach:
                    clean_status_scan = [re.sub(r"<[^>]+>", "", item[0]) for item in cung_st_scan[p]]
                    if not any(val_cat_cach in clean_name for clean_name in clean_status_scan): return False
                    
                # 3. LỌC THIÊN THỜI
                if loc_thien_thoi == "天地干":
                    if stem_colors_scan.get(p, "#000000") == "#000000": return False
                elif loc_thien_thoi == "吉":
                    if stem_colors_scan.get(p, "#000000") == "#000000": return False
                    if than_colors_scan.get(p, "#000000") == "#000000" and mon_colors_scan.get(p, "#000000") == "#000000": return False
                    
                # 4. LỌC NHÂN HÒA
                if loc_nhan_hoa == "吉":
                    _, current_k_col = kigaku_data_scan[p]['stars']['d']
                    if current_k_col == "#000000": return False

                # 5. LỌC CÁT NHẬT
                if loai_ban == "时家" and loc_cat_nhat == "吉":
                    if day_stem_colors_scan.get(p, "#000000") == "#000000": return False
                    if day_than_colors_scan.get(p, "#000000") == "#000000" and day_mon_colors_scan.get(p, "#000000") == "#000000": return False
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
                cach_cuc_cua_cung = cung_st_scan[target_palace]
                
                res_than = scan_data[target_palace]['than']
                res_mon = scan_data[target_palace]['mon']
                res_than_col = than_colors_scan.get(target_palace, "#999999")
                res_mon_col = mon_colors_scan.get(target_palace, "#999999")
                res_thien = scan_data[target_palace]['thien']
                res_dia = scan_data[target_palace]['dia']
                res_stem_col = stem_colors_scan.get(target_palace, "#000000")
                res_stems_html = f"<span style='color:{res_stem_col}; font-weight:bold;'>{res_thien}</span>/<span style='color:{res_stem_col}; font-weight:bold;'>{res_dia}</span>"
                
                d_star_val, d_star_col = kigaku_data_scan[target_palace]['stars']['d']
                d_decor = "underline" if kigaku_data_scan[target_palace].get('honmei') else "none"
                d_style = f"color:{d_star_col}; font-weight:bold; font-size:16px; text-decoration:{d_decor}; text-decoration-color:#000000; text-underline-offset:2px; text-decoration-thickness:2px;"
                kigaku_result_html = f" | Khí Học: <span style='{d_style}'>{d_star_val}</span>"
                
                day_board_html = ""
                if loai_ban == "时家":
                    day_wl_ju = day_star_s
                    day_scan_data, day_can_tuan, _, day_p_land = lap_que_wolong(can_ngay_scan, chi_ngay_scan, wl_dun_s, day_wl_ju, day_star_s)
                    day_can_tuan = get_xun_leader(can_ngay_scan, chi_ngay_scan)
                    
                    day_cung_st_scan, day_stem_colors, day_mon_colors, day_than_colors = qimen_analyzer_hojo(day_scan_data, day_can_tuan, day_p_land)
                    
                    day_cung_day_stars = {p: day_scan_data[p]['day_star'] for p in range(1, 10)}
                    day_kigaku = evaluate_kigaku_formations(b_day_star, day_cung_day_stars, chi_ngay_scan, "日家")
                    
                    d_than = day_scan_data[target_palace]['than']
                    d_mon = day_scan_data[target_palace]['mon']
                    d_thien = day_scan_data[target_palace]['thien']
                    d_dia = day_scan_data[target_palace]['dia']
                    
                    d_than_col = day_than_colors.get(target_palace, "#999999")
                    d_mon_col = day_mon_colors.get(target_palace, "#999999")
                    d_stem_col = day_stem_colors.get(target_palace, "#000000")
                    
                    d_star_val2, d_star_col2 = day_kigaku[target_palace]['stars']['d']
                    d_decor2 = "underline" if day_kigaku[target_palace].get('honmei') else "none"
                    d_style2 = f"color:{d_star_col2}; font-weight:bold; font-size:16px; text-decoration:{d_decor2}; text-decoration-color:#000000; text-underline-offset:2px; text-decoration-thickness:2px;"
                    kigaku_day_html = f" | Khí Học: <span style='{d_style2}'>{d_star_val2}</span>"
                    
                    day_cach_cuc_html = ""
                    if day_cung_st_scan[target_palace]:
                        list_html = []
                        for name, color in day_cung_st_scan[target_palace]:
                            clean_name = re.sub(r"<[^>]+>", "", name)
                            list_html.append(f"<span style='color:{color}; font-weight:bold;'>{clean_name}</span>")
                        day_cach_cuc_html = " ➔ " + ", ".join(list_html)
                        
                    day_stems_html = f"<span style='color:{d_stem_col}; font-weight:bold;'>{d_thien}</span>/<span style='color:{d_stem_col}; font-weight:bold;'>{d_dia}</span>"
                    day_board_html = f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;↳ <b>[Nhật Bàn]</b> | {day_stems_html} | <span style='color:{d_than_col}; font-weight:bold;'>{d_than}</span> - <span style='color:{d_mon_col}; font-weight:bold;'>{d_mon}</span>{day_cach_cuc_html}{kigaku_day_html}"

                results.append((time_str, c_str, ten_cung, cach_cuc_cua_cung, kigaku_result_html, res_than, res_mon, res_than_col, res_mon_col, day_board_html, ly_text_in_ra, res_stems_html, wd_text_in_ra))

        if results:
            st.success(f"**TÌM THẤY {len(results)} KẾT QUẢ:**")
            for idx, (t_str, canchi_str, cung_str, cach_cuc_cua_cung, kigaku_html, t_name, m_name, t_col, m_col, day_board_html, ly_text_in_ra, stems_html, wd_text_in_ra) in enumerate(results):
                h_text = f" | Hướng: {cung_str}" if cung_str else ""
                
                than_mon_html = f" | <span style='color:{t_col}; font-weight:bold;'>{t_name}</span> - <span style='color:{m_col}; font-weight:bold;'>{m_name}</span>"
                
                cach_cuc_html = ""
                if cach_cuc_cua_cung:
                    list_html = []
                    for name, color in cach_cuc_cua_cung:
                        clean_name = re.sub(r"<[^>]+>", "", name)
                        list_html.append(f"<span style='color:{color}; font-weight:bold;'>{clean_name}</span>")
                    cach_cuc_html = " ➔ " + ", ".join(list_html)
                    
                ly_html = f" | <span style='color:#666666; font-weight:bold;'>{ly_text_in_ra}</span>" if ly_text_in_ra else ""
                wd_html = f" | <span style='color:#666666; font-weight:bold;'>{wd_text_in_ra}</span>" if wd_text_in_ra else ""
                
                if loai_ban == "时家":
                    st.markdown(f"{idx+1}. {t_str}{h_text} | {stems_html}{than_mon_html}{cach_cuc_html}{kigaku_html}{ly_html}{wd_html}", unsafe_allow_html=True)
                else:
                    st.markdown(f"{idx+1}. {t_str} | {canchi_str}{h_text} | {stems_html}{than_mon_html}{cach_cuc_html}{kigaku_html}", unsafe_allow_html=True)
                if day_board_html:
                    st.markdown(day_board_html, unsafe_allow_html=True)
                st.markdown("<div style='height: 5px;'></div>", unsafe_allow_html=True)
        else:
            st.warning("Không tìm thấy ngày nào thỏa mãn TẤT CẢ các điều kiện trong 1 năm tới.")
