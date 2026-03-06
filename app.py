import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import urllib.request
import gspread
import os
import textwrap

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="ระบบบันทึกคะแนน V17 (Dynamic Comments)", layout="wide") 
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1ny5m5Yq4V269FdZemV105cDPeVUcp9sGjOyVAbbnA0Q/edit"

# --- 2. โหลดฟอนต์ภาษาไทย ---
@st.cache_resource
def load_thai_font():
    font_url = "https://github.com/google/fonts/raw/main/ofl/sarabun/Sarabun-Regular.ttf"
    font_path = "Sarabun-Regular.ttf"
    if not os.path.exists(font_path): urllib.request.urlretrieve(font_url, font_path)
    fm.fontManager.addfont(font_path)
    return fm.FontProperties(fname=font_path, size=12), fm.FontProperties(fname=font_path, size=16, weight='bold'), fm.FontProperties(fname=font_path, size=20, weight='bold')

prop_normal, prop_title, prop_header = load_thai_font()
prop_comment = fm.FontProperties(fname="Sarabun-Regular.ttf", size=14)

# --- 3. การเชื่อมต่อฐานข้อมูล ---
@st.cache_resource
def get_gspread_client():
    try:
        if "gcp_service_account" in st.secrets: return gspread.service_account_from_dict(dict(st.secrets["gcp_service_account"]))
        else:
            key_file = "cresds.json" if os.path.exists("cresds.json") else "creds.json"
            return gspread.service_account(filename=key_file)
    except: return None

gc = get_gspread_client()
if not gc: st.error("🚨 เชื่อมต่อ Google API ไม่ได้"); st.stop()

try:
    sh = gc.open_by_url(SPREADSHEET_URL)
    master_data = pd.DataFrame(sh.worksheet("StudentList").get_all_records())
    df_topics = pd.DataFrame(sh.worksheet("TopicSettings").get_all_records())
    
    # 🌟 โหลดหน้าต่าง Comments เข้ามาในระบบ 🌟
    try: df_comments = pd.DataFrame(sh.worksheet("Comments").get_all_records())
    except: df_comments = pd.DataFrame()
except:
    st.error("🚨 โหลดข้อมูลเริ่มต้นไม่ได้"); st.stop()

# 🌟 ฟังก์ชันดึงคอมเมนต์ตามช่วงคะแนน (ถอดแบบมาจาก Colab) 🌟
def get_real_comment(subject, total_score):
    if df_comments.empty: return "ไม่พบหน้าตาราง Comments ใน Google Sheets"
    
    col_map = {'คณิตศาสตร์': 'Comment_math', 'วิทยาศาสตร์': 'Comment_sci', 'ภาษาอังกฤษ': 'Comment_eng'}
    target_col = col_map.get(subject)
    
    if not target_col or target_col not in df_comments.columns:
        return f"ไม่พบคอลัมน์ {target_col} ในหน้า Comments"

    for _, row in df_comments.iterrows():
        try:
            range_str = str(row.get('เกณฑ์คะแนน', '')).strip()
            if '-' in range_str:
                min_s, max_s = map(int, range_str.split('-'))
                if min_s <= round(total_score) <= max_s:
                    return str(row[target_col])
        except: continue
    return "คะแนนไม่อยู่ในเกณฑ์ที่ตั้งไว้"

# --- 4. UI INTERFACE ---
st.title("🎓 ระบบจัดการคะแนนและรายงานผล (V17)")
tab_entry, tab_dashboard = st.tabs(["📝 บันทึกข้อมูล", "📊 พิมพ์รายงานผล (Report Card)"])

# ==========================================
# 🌟 TAB 1: บันทึกข้อมูล
# ==========================================
with tab_entry:
    col_form, col_table = st.columns([1, 1.3])
    with col_form:
        target_month = st.selectbox("เลือกเดือน", ["มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน", "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"])
        try:
            ws_current = sh.worksheet(target_month)
            df_month = pd.DataFrame(ws_current.get_all_values())
            df_month.columns = df_month.iloc[0]; df_month = df_month[1:].reset_index(drop=True)
        except: st.error(f"❌ ไม่พบหน้า Sheet ชื่อ '{target_month}'"); st.stop()

        branches = sorted(master_data['Branch'].unique().tolist())
        selected_branch = st.selectbox("สาขา", ["-- โปรดเลือกสาขา --"] + branches)
        names = master_data[master_data['Branch'] == selected_branch]['Name'].tolist() if selected_branch != "-- โปรดเลือกสาขา --" else []
        student_name = st.selectbox("นักเรียน", ["-- โปรดเลือกรายชื่อ --"] + names)

        available_subjects = df_month[df_month.iloc[:, 0].str.strip() == student_name.strip()].iloc[:, 1].unique().tolist()
        selected_subject = st.selectbox("วิชา", ["-- เลือกวิชา --"] + available_subjects)

        label_1, label_2, label_3, db_f1, db_f2, db_f3 = "ด.1", "ด.2", "ด.3", 10, 10, 10
        if selected_subject != "-- เลือกวิชา --":
            match_topic = df_topics[(df_topics['Month'].astype(str).str.strip() == target_month.strip()) & (df_topics['Subject'].astype(str).str.strip() == selected_subject.strip())]
            if not match_topic.empty:
                row = match_topic.iloc[0]
                label_1, label_2, label_3 = row.get('Topic_1','') or "ด.1", row.get('Topic_2','') or "ด.2", row.get('Topic_3','') or "ด.3"
                try: db_f1 = int(row.get('FullScore_1', 10))
                except: pass
                try: db_f2 = int(row.get('FullScore_2', 10))
                except: pass
                try: db_f3 = int(row.get('FullScore_3', 10))
                except: pass

            st.divider()
            c1, c2, c3 = st.columns(3)
            with c1: ui_f1 = st.number_input(f"เต็ม: {label_1}", min_value=1, value=db_f1)
            with c2: ui_f2 = st.number_input(f"เต็ม: {label_2}", min_value=1, value=db_f2)
            with c3: ui_f3 = st.number_input(f"เต็ม: {label_3}", min_value=1, value=db_f3)

            with st.form("update_v17"):
                year = st.selectbox("ปีการศึกษา", ["2569", "2570"])
                s1 = st.number_input(f"{label_1} (ได้)", 0, ui_f1)
                s2 = st.number_input(f"{label_2} (ได้)", 0, ui_f2)
                s3 = st.number_input(f"{label_3} (ได้)", 0, ui_f3)
                
                if st.form_submit_button("🚀 บันทึกข้อมูล"):
                    try:
                        found = False
                        for i, r in enumerate(ws_current.get_all_values()):
                            if r[0].strip() == student_name.strip() and r[1].strip() == selected_subject.strip():
                                ws_current.update(f"C{i+1}:H{i+1}", [[target_month, year, selected_branch, s1, s2, s3]])
                                st.success("✅ บันทึกสำเร็จ!"); st.balloons(); st.rerun(); break
                        if not found: st.error("❌ ไม่พบเป้าหมาย")
                    except Exception as e: st.error(f"🚨 ข้อผิดพลาด: {e}")

    with col_table:
        st.subheader(f"🔍 ตาราง: {target_month}")
        if not df_month.empty:
            display_df = df_month.copy()
            if selected_branch != "-- โปรดเลือกสาขา --": display_df = display_df[display_df.iloc[:, 4] == selected_branch]
            st.dataframe(display_df, use_container_width=True, height=600)

# ==========================================
# 🌟 TAB 2: กราฟ + ดึงคอมเมนต์อัตโนมัติตามช่วงคะแนน
# ==========================================
with tab_dashboard:
    st.subheader(f"📄 พิมพ์รายงานผลการเรียนรู้ รอบเดือน {target_month}")
    
    if not df_month.empty:
        all_students = sorted([n for n in df_month.iloc[:, 0].astype(str).str.strip().unique().tolist() if n])
        report_student = st.selectbox("เลือกนักเรียน", ["-- เลือกนักเรียน --"] + all_students)

        if report_student != "-- เลือกนักเรียน --":
            student_data = df_month[df_month.iloc[:, 0].str.strip() == report_student]
            subjects_taken = student_data.iloc[:, 1].str.strip().tolist()

            if subjects_taken:
                fig = plt.figure(figsize=(18, 12))
                gs = fig.add_gridspec(2, 3, width_ratios=[1, 1, 1.2], hspace=0.3, wspace=0.3)
                fig.suptitle(f'รายงานผลการเรียนรู้: {report_student} (เดือน {target_month})', fontproperties=prop_header, fontsize=28, y=0.98)

                ax_dict = {
                    "คณิตศาสตร์": fig.add_subplot(gs[0, 0:2], polar=True),
                    "วิทยาศาสตร์": fig.add_subplot(gs[1, 0], polar=True),
                    "ภาษาอังกฤษ": fig.add_subplot(gs[1, 1], polar=True)
                }
                colors = {"คณิตศาสตร์": "blue", "วิทยาศาสตร์": "red", "ภาษาอังกฤษ": "green"}
                ax_text = fig.add_subplot(gs[:, 2]); ax_text.axis('off')
                
                comment_texts = {"คณิตศาสตร์": "ยังไม่มีข้อมูล", "วิทยาศาสตร์": "ยังไม่มีข้อมูล", "ภาษาอังกฤษ": "ยังไม่มีข้อมูล"}

                for subj in subjects_taken:
                    if subj not in ax_dict: continue
                    ax = ax_dict[subj]
                    
                    t_labels, t_fulls = ["T1", "T2", "T3"], [10, 10, 10]
                    match_topic = df_topics[(df_topics['Month'].astype(str).str.strip() == target_month) & (df_topics['Subject'].astype(str).str.strip() == subj)]
                    if not match_topic.empty:
                        row = match_topic.iloc[0]
                        t_labels = [row.get('Topic_1','') or "T1", row.get('Topic_2','') or "T2", row.get('Topic_3','') or "T3"]
                        try: t_fulls = [int(row.get('FullScore_1', 10)), int(row.get('FullScore_2', 10)), int(row.get('FullScore_3', 10))]
                        except: pass

                    subj_row = student_data[student_data.iloc[:, 1].str.strip() == subj].iloc[0]
                    try: scores_raw = [float(subj_row.iloc[5]) if str(subj_row.iloc[5]).strip() else 0, float(subj_row.iloc[6]) if str(subj_row.iloc[6]).strip() else 0, float(subj_row.iloc[7]) if str(subj_row.iloc[7]).strip() else 0]
                    except: scores_raw = [0, 0, 0]

                    scores_norm = [(s/f)*10 if f>0 else 0 for s, f in zip(scores_raw, t_fulls)]
                    total_score = sum(scores_raw)

                    # พล็อตกราฟ
                    angles = [n / float(3) * 2 * np.pi for n in range(3)]
                    angles += angles[:1]; scores_norm += scores_norm[:1]
                    ax.set_theta_offset(np.pi / 2); ax.set_theta_direction(-1)
                    ax.set_xticks(angles[:-1]); ax.set_xticklabels(t_labels, fontproperties=prop_normal)
                    ax.set_yticks(np.arange(0, 11, 2)); ax.set_ylim(0, 10)
                    
                    line_color = colors.get(subj, "gray")
                    ax.plot(angles, scores_norm, color=line_color, linewidth=2)
                    ax.fill(angles, scores_norm, color=line_color, alpha=0.25)
                    ax.set_title(f"วิชา {subj}", color=line_color, y=1.1, fontproperties=prop_title)

                    # 🌟 ดึงคอมเมนต์ของจริงจาก Google Sheets 🌟
                    fetched_comment = get_real_comment(subj, total_score)
                    comment_texts[subj] = f"คะแนนรวม: {total_score}/{sum(t_fulls)}\nความเห็น: {fetched_comment}"

                for subj, ax in ax_dict.items():
                    if subj not in subjects_taken: ax.axis('off')

                # พิมพ์ข้อความลงพื้นที่ฝั่งขวา
                y_positions = {"คณิตศาสตร์": 0.85, "วิทยาศาสตร์": 0.50, "ภาษาอังกฤษ": 0.15}
                for subj in ["คณิตศาสตร์", "วิทยาศาสตร์", "ภาษาอังกฤษ"]:
                    ax_text.text(0.0, y_positions[subj], f"รายงานผล: {subj}", color=colors.get(subj, "black"), fontproperties=prop_title, ha='left', va='bottom')
                    wrapped_text = "\n".join(textwrap.wrap(comment_texts[subj], width=45))
                    ax_text.text(0.0, y_positions[subj] - 0.05, wrapped_text, color='#333333', fontproperties=prop_comment, ha='left', va='top')

                st.pyplot(fig)
            else: st.info("ไม่พบข้อมูลวิชาของนักเรียนคนนี้")