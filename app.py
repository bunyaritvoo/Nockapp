import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
import os

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="ระบบบันทึกคะแนน V10 (Monthly Mode)", layout="wide") 

SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1ny5m5Yq4V269FdZemV105cDPeVUcp9sGjOyVAbbnA0Q/edit"

# --- 2. ระบบเชื่อมต่อฐานข้อมูล ---
@st.cache_resource
def get_gspread_client():
    try:
        if "gcp_service_account" in st.secrets:
            # สำหรับใช้งานบน Streamlit Cloud
            return gspread.service_account_from_dict(dict(st.secrets["gcp_service_account"]))
        else:
            # สำหรับรันในเครื่อง (ตรวจชื่อไฟล์ตามที่คุณบาสตั้ง)
            for key in ["cresds.json", "creds.json", "cresds"]:
                if os.path.exists(key):
                    return gspread.service_account(filename=key)
        return None
    except Exception as e:
        st.error(f"🚨 เชื่อมต่อไม่ได้: {e}")
        return None

gc = get_gspread_client()

if not gc:
    st.stop()

try:
    sh = gc.open_by_url(SPREADSHEET_URL)
    # ดึงรายชื่อ Master (Name, Branch) จากหน้า StudentList
    ws_list = sh.worksheet("StudentList")
    master_data = pd.DataFrame(ws_list.get_all_records())
    master_data['Name'] = master_data['Name'].astype(str).str.strip()
    master_data['Branch'] = master_data['Branch'].astype(str).str.strip()
except Exception as e:
    st.error(f"🚨 ปัญหาการโหลดข้อมูลเริ่มต้น: {e}")
    st.stop()

# --- 3. UI INTERFACE ---
st.title("🎓 ระบบจัดการคะแนนสอบ ติวเข้าม.1")
st.divider()

col_form, col_table = st.columns([1, 1.3])

with col_form:
    st.subheader("📝 บันทึกข้อมูล")
    
    # 1. เลือกเดือน (ระบบจะใช้ชื่อนี้กระโดดไปหาหน้า Tab)
    target_month = st.selectbox("เลือกเดือนที่ต้องการบันทึก", 
                                ["มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน", 
                                 "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"])
    
    try:
        # ดึงข้อมูลจากชีทประจำเดือนมาเตรียมค้นหา
        ws_current = sh.worksheet(target_month)
        df_month = pd.DataFrame(ws_current.get_all_records())
    except:
        st.error(f"❌ ไม่พบหน้า Sheet ชื่อ '{target_month}' กรุณาสร้าง Tab ให้ครบทุกเดือนนะครับ")
        st.stop()

    # 2. เลือกสาขาและชื่อ (กรองจาก StudentList)
    all_branches = sorted(master_data['Branch'].unique().tolist())
    selected_branch = st.selectbox("สาขา", ["-- โปรดเลือกสาขา --"] + all_branches)
    
    if selected_branch != "-- โปรดเลือกสาขา --":
        names_in_branch = master_data[master_data['Branch'] == selected_branch]['Name'].tolist()
    else:
        names_in_branch = []
    student_name = st.selectbox("เลือกชื่อนักเรียน", ["-- โปรดเลือกรายชื่อ --"] + names_in_branch)

    # 3. เลือกวิชา (กรองจากรายวิชาที่มีในหน้าเดือนนั้นๆ ของนักเรียนคนนี้)
    if student_name != "-- โปรดเลือกรายชื่อ --" and not df_month.empty:
        available_subjects = df_month[df_month['Student_Name'].astype(str).str.strip() == student_name]['Subject'].unique().tolist()
    else:
        available_subjects = []
    selected_subject = st.selectbox("วิชา", ["-- เลือกวิชา --"] + available_subjects)

    with st.form("score_v10_form", clear_on_submit=True):
        year = st.selectbox("ปีการศึกษา", ["2569", "2570", "2571"])
        st.divider()
        st.write("📊 **คะแนนสอบ**")
        s1 = st.number_input("ด้านที่ 1", 0, 100, step=1)
        s2 = st.number_input("ด้านที่ 2", 0, 100, step=1)
        s3 = st.number_input("ด้านที่ 3", 0, 100, step=1)
        
        submitted = st.form_submit_button(f"🚀 อัปเดตข้อมูลลงชีท {target_month}")

        if submitted:
            if student_name != "-- โปรดเลือกรายชื่อ --" and selected_subject != "-- เลือกวิชา --":
                try:
                    # ค้นหาแถวที่ Name และ Subject ตรงกันเป๊ะ
                    match = df_month[(df_month['Student_Name'].astype(str).str.strip() == student_name) & 
                                     (df_month['Subject'].astype(str).str.strip() == selected_subject)]
                    
                    if not match.empty:
                        row_idx = match.index[0] + 2 # +2 เพราะ Index เริ่มที่ 0 และมีหัวตาราง
                        
                        # อัปเดตตามคอลัมน์ในรูป: C=Month, D=Year, E=Branch, F=S1, G=S2, H=S3
                        update_values = [[target_month, year, selected_branch, s1, s2, s3]]
                        ws_current.update(f"C{row_idx}:H{row_idx}", update_values)
                        
                        st.success(f"✅ บันทึกคะแนน {selected_subject} ของ {student_name} สำเร็จ!")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error(f"❌ ไม่พบแถวของ {student_name} วิชา {selected_subject} ในหน้า {target_month}")
                except Exception as e:
                    st.error(f"🚨 เกิดข้อผิดพลาด: {e}")
            else:
                st.warning("⚠️ กรุณาเลือกรายชื่อและวิชาให้ครบถ้วน")

with col_table:
    st.subheader(f"🔍 ข้อมูลการบันทึก: {target_month}")
    if not df_month.empty:
        # กรองตารางฝั่งขวาตามสาขาที่เลือก
        display_df = df_month.copy()
        if selected_branch != "-- โปรดเลือกสาขา --":
            display_df = display_df[display_df['Branch'] == selected_branch]
        st.dataframe(display_df, use_container_width=True, height=600)
    else:
        st.info("ยังไม่มีข้อมูลในชีทนี้")