import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
import os

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="ระบบบันทึกคะแนน V11 (Dynamic Topics)", layout="wide") 

SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1ny5m5Yq4V269FdZemV105cDPeVUcp9sGjOyVAbbnA0Q/edit"

# --- 2. การเชื่อมต่อฐานข้อมูล ---
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
    
    # 1. โหลดข้อมูลรายชื่อ (StudentList)
    ws_list = sh.worksheet("StudentList")
    master_data = pd.DataFrame(ws_list.get_all_records())
    
    # 2. โหลดข้อมูลหัวข้อคะแนน (TopicSettings) - ที่คุณบาสเพิ่งสร้าง
    ws_topics = sh.worksheet("TopicSettings")
    df_topics = pd.DataFrame(ws_topics.get_all_records())
    
except Exception as e:
    st.error(f"🚨 โหลดข้อมูลเริ่มต้นไม่ได้: {e} (อย่าลืมสร้างแผ่นงานชื่อ TopicSettings นะครับ)")
    st.stop()

# --- 3. UI INTERFACE ---
st.title("🎓 ระบบจัดการคะแนน (เปลี่ยนหัวข้ออัตโนมัติ)")

col_form, col_table = st.columns([1, 1.3])

with col_form:
    st.subheader("📝 บันทึกข้อมูล")
    
    # เลือกเดือน
    target_month = st.selectbox("เลือกเดือน", 
                                ["มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน", 
                                 "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"])
    
    try:
        ws_current = sh.worksheet(target_month)
        df_month = pd.DataFrame(ws_current.get_all_values())
        df_month.columns = df_month.iloc[0] 
        df_month = df_month[1:].reset_index(drop=True)
    except:
        st.error(f"❌ ไม่พบหน้า Sheet ชื่อ '{target_month}'")
        st.stop()

    # เลือกสาขาและชื่อ
    branches = sorted(master_data['Branch'].unique().tolist())
    selected_branch = st.selectbox("สาขา", ["-- โปรดเลือกสาขา --"] + branches)
    
    names = master_data[master_data['Branch'] == selected_branch]['Name'].tolist() if selected_branch != "-- โปรดเลือกสาขา --" else []
    student_name = st.selectbox("นักเรียน", ["-- โปรดเลือกรายชื่อ --"] + names)

    # เลือกวิชา
    available_subjects = df_month[df_month.iloc[:, 0].str.strip() == student_name.strip()].iloc[:, 1].unique().tolist()
    selected_subject = st.selectbox("วิชา", ["-- เลือกวิชา --"] + available_subjects)

    # ==========================================
    # 🌟 ระบบ DYNAMIC TOPICS (เปลี่ยนชื่อหัวข้อ) 🌟
    # ==========================================
    # ตั้งค่าเริ่มต้นเผื่อหาไม่เจอ
    label_1, label_2, label_3 = "ด้านที่ 1", "ด้านที่ 2", "ด้านที่ 3"
    
    if selected_subject != "-- เลือกวิชา --":
        # ค้นหาหัวข้อจาก TopicSettings ตามเดือนและวิชาที่เลือก
        match_topic = df_topics[(df_topics['Month'].astype(str).str.strip() == target_month.strip()) & 
                                (df_topics['Subject'].astype(str).str.strip() == selected_subject.strip())]
        
        if not match_topic.empty:
            # ดึงชื่อหัวข้อมาเปลี่ยน ถ้าช่องใน Sheet ว่าง จะใช้ชื่อ Default แทน
            label_1 = match_topic.iloc[0].get('Topic_1', '') or "ด้านที่ 1"
            label_2 = match_topic.iloc[0].get('Topic_2', '') or "ด้านที่ 2"
            label_3 = match_topic.iloc[0].get('Topic_3', '') or "ด้านที่ 3"

    with st.form("update_v11"):
        year = st.selectbox("ปีการศึกษา", ["2569", "2570"])
        st.divider()
        st.markdown(f"**📌 ระบุคะแนน: {selected_subject}**")
        
        # ใช้ชื่อ Label ที่ดึงมาจาก Sheet
        s1 = st.number_input(str(label_1), 0, 100)
        s2 = st.number_input(str(label_2), 0, 100)
        s3 = st.number_input(str(label_3), 0, 100)
        
        submitted = st.form_submit_button("🚀 อัปเดตข้อมูล")

        if submitted and student_name != "-- โปรดเลือกรายชื่อ --" and selected_subject != "-- เลือกวิชา --":
            try:
                found = False
                all_values = ws_current.get_all_values()
                for i, row in enumerate(all_values):
                    if row[0].strip() == student_name.strip() and row[1].strip() == selected_subject.strip():
                        row_idx = i + 1
                        ws_current.update(f"C{row_idx}:H{row_idx}", [[target_month, year, selected_branch, s1, s2, s3]])
                        st.success(f"✅ บันทึกคะแนนสำเร็จ!")
                        st.balloons()
                        found = True
                        st.rerun()
                        break
                if not found:
                    st.error(f"❌ ไม่พบเป้าหมายในชีท")
            except Exception as e:
                st.error(f"🚨 ข้อผิดพลาด: {e}")

with col_table:
    st.subheader(f"🔍 ตารางตรวจสอบ: {target_month}")
    if not df_month.empty:
        display_df = df_month.copy()
        if selected_branch != "-- โปรดเลือกสาขา --":
            display_df = display_df[display_df.iloc[:, 4] == selected_branch]
        
        # เปลี่ยนหัวคอลัมน์ S1, S2, S3 ให้เป็นชื่อ Topic จริงๆ สำหรับโชว์ในตารางด้วย!
        if selected_subject != "-- เลือกวิชา --" and not match_topic.empty:
            display_df.rename(columns={
                display_df.columns[5]: str(label_1), # F = S1
                display_df.columns[6]: str(label_2), # G = S2
                display_df.columns[7]: str(label_3)  # H = S3
            }, inplace=True)
            
        st.dataframe(display_df, use_container_width=True, height=600)