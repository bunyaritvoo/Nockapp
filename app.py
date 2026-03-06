import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import urllib.request
import gspread
import os

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="ระบบบันทึกคะแนน V14 (Radar Dashboard)", layout="wide") 
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1ny5m5Yq4V269FdZemV105cDPeVUcp9sGjOyVAbbnA0Q/edit"

# --- 2. ฟังก์ชันโหลดฟอนต์ภาษาไทย (สำหรับแสดงในกราฟ) ---
@st.cache_resource
def load_thai_font():
    font_url = "https://github.com/google/fonts/raw/main/ofl/sarabun/Sarabun-Regular.ttf"
    font_path = "Sarabun-Regular.ttf"
    # ถ้ายังไม่มีไฟล์ฟอนต์ในระบบ ให้ดาวน์โหลดมา
    if not os.path.exists(font_path):
        urllib.request.urlretrieve(font_url, font_path)
    fm.fontManager.addfont(font_path)
    return fm.FontProperties(fname=font_path, size=14), fm.FontProperties(fname=font_path, size=18, weight='bold')

prop_normal, prop_title = load_thai_font()

# --- 3. การเชื่อมต่อฐานข้อมูล ---
@st.cache_resource
def get_gspread_client():
    try:
        if "gcp_service_account" in st.secrets:
            return gspread.service_account_from_dict(dict(st.secrets["gcp_service_account"]))
        else:
            key_file = "cresds.json" if os.path.exists("cresds.json") else "creds.json"
            return gspread.service_account(filename=key_file)
    except Exception as e:
        return None

gc = get_gspread_client()

if not gc:
    st.error("🚨 เชื่อมต่อ Google API ไม่ได้ ตรวจสอบ Secrets หรือไฟล์ JSON ครับ")
    st.stop()

try:
    sh = gc.open_by_url(SPREADSHEET_URL)
    ws_list = sh.worksheet("StudentList")
    master_data = pd.DataFrame(ws_list.get_all_records())
    
    ws_topics = sh.worksheet("TopicSettings")
    df_topics = pd.DataFrame(ws_topics.get_all_records())
except Exception as e:
    st.error(f"🚨 โหลดข้อมูลเริ่มต้นไม่ได้: {e}")
    st.stop()

# --- 4. UI INTERFACE (แบ่ง 2 Tabs) ---
st.title("🎓 ระบบจัดการคะแนนและวิเคราะห์ผล (Radar Chart)")

tab_entry, tab_dashboard = st.tabs(["📝 บันทึกข้อมูล", "📊 รายงานผลรายบุคคล (Radar Chart)"])

# ==========================================
# 🌟 TAB 1: บันทึกข้อมูล (โค้ดเดิม V13)
# ==========================================
with tab_entry:
    col_form, col_table = st.columns([1, 1.3])

    with col_form:
        target_month = st.selectbox("เลือกเดือน", ["มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน", "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"])
        
        try:
            ws_current = sh.worksheet(target_month)
            df_month = pd.DataFrame(ws_current.get_all_values())
            df_month.columns = df_month.iloc[0] 
            df_month = df_month[1:].reset_index(drop=True)
        except:
            st.error(f"❌ ไม่พบหน้า Sheet ชื่อ '{target_month}'")
            st.stop()

        branches = sorted(master_data['Branch'].unique().tolist())
        selected_branch = st.selectbox("สาขา", ["-- โปรดเลือกสาขา --"] + branches)
        names = master_data[master_data['Branch'] == selected_branch]['Name'].tolist() if selected_branch != "-- โปรดเลือกสาขา --" else []
        student_name = st.selectbox("นักเรียน", ["-- โปรดเลือกรายชื่อ --"] + names)

        available_subjects = df_month[df_month.iloc[:, 0].str.strip() == student_name.strip()].iloc[:, 1].unique().tolist()
        selected_subject = st.selectbox("วิชา", ["-- เลือกวิชา --"] + available_subjects)

        label_1, label_2, label_3 = "ด้านที่ 1", "ด้านที่ 2", "ด้านที่ 3"
        db_f1, db_f2, db_f3 = 10, 10, 10
        
        if selected_subject != "-- เลือกวิชา --":
            match_topic = df_topics[(df_topics['Month'].astype(str).str.strip() == target_month.strip()) & (df_topics['Subject'].astype(str).str.strip() == selected_subject.strip())]
            if not match_topic.empty:
                row_data = match_topic.iloc[0]
                label_1, label_2, label_3 = row_data.get('Topic_1', '') or "ด้านที่ 1", row_data.get('Topic_2', '') or "ด้านที่ 2", row_data.get('Topic_3', '') or "ด้านที่ 3"
                try: db_f1 = int(row_data.get('FullScore_1', 10))
                except: db_f1 = 10
                try: db_f2 = int(row_data.get('FullScore_2', 10))
                except: db_f2 = 10
                try: db_f3 = int(row_data.get('FullScore_3', 10))
                except: db_f3 = 10

            st.divider()
            c1, c2, c3 = st.columns(3)
            with c1: ui_f1 = st.number_input(f"เต็ม: {label_1}", min_value=1, value=db_f1)
            with c2: ui_f2 = st.number_input(f"เต็ม: {label_2}", min_value=1, value=db_f2)
            with c3: ui_f3 = st.number_input(f"เต็ม: {label_3}", min_value=1, value=db_f3)

            with st.form("update_v14"):
                year = st.selectbox("ปีการศึกษา", ["2569", "2570"])
                s1 = st.number_input(f"{label_1} (ได้)", 0, ui_f1)
                s2 = st.number_input(f"{label_2} (ได้)", 0, ui_f2)
                s3 = st.number_input(f"{label_3} (ได้)", 0, ui_f3)
                
                if st.form_submit_button("🚀 บันทึกข้อมูล"):
                    try:
                        found = False
                        all_values = ws_current.get_all_values()
                        for i, row in enumerate(all_values):
                            if row[0].strip() == student_name.strip() and row[1].strip() == selected_subject.strip():
                                row_idx = i + 1
                                ws_current.update(f"C{row_idx}:H{row_idx}", [[target_month, year, selected_branch, s1, s2, s3]])
                                st.success("✅ บันทึกสำเร็จ!")
                                found = True
                                st.rerun()
                                break
                        if not found: st.error("❌ ไม่พบเป้าหมาย")
                    except Exception as e: st.error(f"🚨 ข้อผิดพลาด: {e}")

    with col_table:
        st.subheader(f"🔍 ตาราง: {target_month}")
        if not df_month.empty:
            display_df = df_month.copy()
            if selected_branch != "-- โปรดเลือกสาขา --":
                display_df = display_df[display_df.iloc[:, 4] == selected_branch]
            st.dataframe(display_df, use_container_width=True, height=600)

# ==========================================
# 🌟 TAB 2: Radar Dashboard (แปลงจาก Colab ของคุณบาส)
# ==========================================
with tab_dashboard:
    st.subheader(f"📈 ผลการเรียนรู้รายบุคคล รอบเดือน {target_month}")
    
    # 1. ให้ครูเลือกชื่อเด็กที่จะดู Report
    if not df_month.empty:
        all_students_in_month = sorted(df_month.iloc[:, 0].astype(str).str.strip().unique().tolist())
        # ลบชื่อว่างๆ ออก
        all_students_in_month = [name for name in all_students_in_month if name] 
        report_student = st.selectbox("เลือกนักเรียนเพื่อดู Radar Chart", ["-- เลือกนักเรียน --"] + all_students_in_month)

        if report_student != "-- เลือกนักเรียน --":
            # 2. กรองข้อมูลเฉพาะเด็กคนนี้
            student_data = df_month[df_month.iloc[:, 0].str.strip() == report_student]
            subjects_taken = student_data.iloc[:, 1].str.strip().tolist()

            if subjects_taken:
                st.write(f"กำลังแสดงกราฟของ: **{report_student}** จำนวน {len(subjects_taken)} วิชา")
                
                # 3. เตรียมพื้นที่วาดกราฟ (ขนาดจะปรับตามจำนวนวิชา)
                cols = st.columns(min(len(subjects_taken), 3)) # โชว์สูงสุด 3 กราฟใน 1 แถว
                colors = ['blue', 'red', 'green', 'purple', 'orange']

                # 4. วนลูปวาดกราฟแต่ละวิชา
                for idx, subj in enumerate(subjects_taken):
                    # หาหัวข้อและคะแนนเต็มจาก TopicSettings
                    t_labels = ["ด้านที่ 1", "ด้านที่ 2", "ด้านที่ 3"]
                    t_fulls = [10, 10, 10]
                    
                    match_topic = df_topics[(df_topics['Month'].astype(str).str.strip() == target_month) & 
                                            (df_topics['Subject'].astype(str).str.strip() == subj)]
                    
                    if not match_topic.empty:
                        row = match_topic.iloc[0]
                        t_labels = [row.get('Topic_1', '') or "T1", row.get('Topic_2', '') or "T2", row.get('Topic_3', '') or "T3"]
                        try: t_fulls = [int(row.get('FullScore_1', 10)), int(row.get('FullScore_2', 10)), int(row.get('FullScore_3', 10))]
                        except: pass

                    # หาคะแนนที่เด็กทำได้จาก df_month (คอลัมน์ F, G, H หรือ Index 5, 6, 7)
                    subj_row = student_data[student_data.iloc[:, 1].str.strip() == subj].iloc[0]
                    try:
                        scores_raw = [
                            float(subj_row.iloc[5]) if str(subj_row.iloc[5]).strip() else 0,
                            float(subj_row.iloc[6]) if str(subj_row.iloc[6]).strip() else 0,
                            float(subj_row.iloc[7]) if str(subj_row.iloc[7]).strip() else 0
                        ]
                    except:
                        scores_raw = [0, 0, 0]

                    # 5. แปลงคะแนน (Normalize) ให้เต็ม 10 เหมือนใน Colab
                    scores_norm = []
                    for s, f in zip(scores_raw, t_fulls):
                        if f > 0: scores_norm.append((s / f) * 10)
                        else: scores_norm.append(0)

                    # 6. สร้างกราฟ Radar (Matplotlib)
                    fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))
                    
                    # ปิดมุม (Pad) ให้กราฟเส้นบรรจบกัน
                    angles = [n / float(3) * 2 * np.pi for n in range(3)]
                    angles += angles[:1]
                    scores_norm += scores_norm[:1]

                    ax.set_theta_offset(np.pi / 2)
                    ax.set_theta_direction(-1)
                    ax.set_xticks(angles[:-1])
                    ax.set_xticklabels(t_labels, fontproperties=prop_normal)
                    ax.set_yticks(np.arange(0, 11, 2))
                    ax.set_ylim(0, 10)
                    
                    line_color = colors[idx % len(colors)]
                    ax.plot(angles, scores_norm, color=line_color, linewidth=2)
                    ax.fill(angles, scores_norm, color=line_color, alpha=0.25)
                    ax.set_title(f"วิชา {subj}", color=line_color, y=1.1, fontproperties=prop_title)

                    # 7. โชว์กราฟลงใน Column ของ Streamlit
                    with cols[idx % 3]:
                        st.pyplot(fig)
                        
                        # โชว์ตารางคะแนนเล็กๆ ใต้กราฟ
                        score_df = pd.DataFrame({"หัวข้อ": t_labels, "คะแนนที่ได้": scores_raw, "คะแนนเต็ม": t_fulls})
                        st.dataframe(score_df, hide_index=True)
            else:
                st.info("ไม่พบข้อมูลวิชาของนักเรียนคนนี้ในเดือนที่เลือก")
    else:
        st.info("กรุณาบันทึกข้อมูลอย่างน้อย 1 คน เพื่อดูรายงานครับ")