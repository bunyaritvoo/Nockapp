import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
import os

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="ระบบบันทึกคะแนนกรอกคะแนนติวเข้าม.1", layout="wide") 

SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1ny5m5Yq4V269FdZemV105cDPeVUcp9sGjOyVAbbnA0Q/edit"

# --- 2. การเชื่อมต่อฐานข้อมูล ---
@st.cache_resource
def get_gspread_client():
    try:
        if "gcp_service_account" in st.secrets:
            return gspread.service_account_from_dict(dict(st.secrets["gcp_service_account"]))
        else:
            # ตรวจสอบชื่อไฟล์ในเครื่องให้ตรงกับ cresds.json
            key_file = "cresds.json" if os.path.exists("cresds.json") else "creds.json"
            return gspread.service_account(filename=key_file)
    except Exception as e:
        return None

gc = get_gspread_client()

if not gc:
    st.error("🚨 เชื่อมต่อ Google API ไม่ได้ ตรวจสอบ Secrets (TOML) หรือไฟล์ JSON ครับ")
    st.stop()

try:
    sh = gc.open_by_url(SPREADSHEET_URL)
    ws_list = sh.worksheet("StudentList")
    # ดึงรายชื่อจาก StudentList (A=Name, B=Branch)
    master_data = pd.DataFrame(ws_list.get_all_records())
except Exception as e:
    st.error(f"🚨 โหลดข้อมูลเริ่มต้นไม่ได้: {e}")
    st.stop()

# --- 3. UI ---
st.title("🎓 ระบบจัดการคะแนนสอบติวเข้าม.1 ")

col_form, col_table = st.columns([1, 1.3])

with col_form:
    st.subheader("📝 บันทึกข้อมูล")
    
    target_month = st.selectbox("เลือกเดือน", 
                                ["มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน", 
                                 "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"])
    
    try:
        ws_current = sh.worksheet(target_month)
        # ดึงข้อมูลทุกอย่างมาลบช่องว่างทิ้งก่อนค้นหา
        df_month = pd.DataFrame(ws_current.get_all_values())
        df_month.columns = df_month.iloc[0] # ตั้งแถวแรกเป็นหัวตาราง
        df_month = df_month[1:].reset_index(drop=True)
    except:
        st.error(f"❌ ไม่พบหน้า Sheet ชื่อ '{target_month}'")
        st.stop()

    branches = sorted(master_data['Branch'].unique().tolist())
    selected_branch = st.selectbox("สาขา", ["-- โปรดเลือกสาขา --"] + branches)
    
    names = master_data[master_data['Branch'] == selected_branch]['Name'].tolist() if selected_branch != "-- โปรดเลือกสาขา --" else []
    student_name = st.selectbox("นักเรียน", ["-- โปรดเลือกรายชื่อ --"] + names)

    # ค้นหาวิชาจากคอลัมน์ B (Subject) ของเด็กคนนี้ใน Sheet เดือนนั้นๆ
    # ใช้ .iloc[:, 0] แทนชื่อคอลัมน์เพื่อความชัวร์
    available_subjects = df_month[df_month.iloc[:, 0].str.strip() == student_name.strip()].iloc[:, 1].unique().tolist()
    selected_subject = st.selectbox("วิชา", ["-- เลือกวิชา --"] + available_subjects)

    with st.form("update_v10"):
        year = st.selectbox("ปีการศึกษา", ["2569", "2570"])
        s1 = st.number_input("ด้านที่ 1", 0, 100)
        s2 = st.number_input("ด้านที่ 2", 0, 100)
        s3 = st.number_input("ด้านที่ 3", 0, 100)
        
        submitted = st.form_submit_button("🚀 อัปเดตข้อมูล")

        if submitted and student_name != "-- โปรดเลือกรายชื่อ --" and selected_subject != "-- เลือกวิชา --":
            try:
                # ระบบค้นหาแบบยืดหยุ่น (ไม่สนชื่อคอลัมน์ สนแค่ลำดับ A และ B)
                found = False
                all_values = ws_current.get_all_values()
                for i, row in enumerate(all_values):
                    # เช็กแถวที่คอลัมน์ A ตรงกับชื่อ และ คอลัมน์ B ตรงกับวิชา
                    if row[0].strip() == student_name.strip() and row[1].strip() == selected_subject.strip():
                        row_idx = i + 1
                        # อัปเดต C=Month, D=Year, E=Branch, F=S1, G=S2, H=S3
                        ws_current.update(f"C{row_idx}:H{row_idx}", [[target_month, year, selected_branch, s1, s2, s3]])
                        st.success(f"✅ บันทึกสำเร็จที่แถว {row_idx}!")
                        st.balloons()
                        found = True
                        st.rerun()
                        break
                if not found:
                    st.error(f"❌ ไม่พบ {student_name} วิชา {selected_subject} ในหน้า {target_month}")
            except Exception as e:
                st.error(f"🚨 ข้อผิดพลาด: {e}")

with col_table:
    st.subheader(f"🔍 ตาราง: {target_month}")
    if not df_month.empty:
        display_df = df_month.copy()
        if selected_branch != "-- โปรดเลือกสาขา --":
            # กรองจากคอลัมน์ที่ 5 (Branch)
            display_df = display_df[display_df.iloc[:, 4] == selected_branch]
        st.dataframe(display_df, use_container_width=True, height=600)