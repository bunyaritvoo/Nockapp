import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
import os

# --- CONFIG ---
st.set_page_config(page_title="ระบบบันทึกคะแนนกลาง (Online Mode)", layout="centered")

SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1ny5m5Yq4V269FdZemV105cDPeVUcp9sGjOyVAbbnA0Q/edit"

# --- 1. ระบบเชื่อมต่อ (รองรับทั้งในคอมและบนเว็บออนไลน์) ---
try:
    # กรณีอยู่บนเว็บออนไลน์ (Streamlit Cloud) ให้ดึงกุญแจจากระบบ Secrets
    if "gcp_service_account" in st.secrets:
        creds_dict = dict(st.secrets["gcp_service_account"])
        gc = gspread.service_account_from_dict(creds_dict)
    else:
        # กรณีรันทดสอบในคอมพิวเตอร์ตัวเอง ให้หาไฟล์ .json
        key_file = None
        for filename in ["creds.json", "cresds.json", "creds", "cresds"]:
            if os.path.exists(filename):
                key_file = filename
                break
        gc = gspread.service_account(filename=key_file)
        
    sh = gc.open_by_url(SPREADSHEET_URL)
    worksheet = sh.sheet1
except Exception as e:
    st.error("🚨 ไม่สามารถเชื่อมต่อฐานข้อมูลได้!")
    st.stop()

# --- UI INTERFACE ---
st.title("📊 ระบบบันทึกคะแนนสอบวัดผลกลาง (ม.1)")

with st.form("score_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        branch = st.selectbox("เลือกสาขา", ["สำนักงานใหญ่", "สาขาที่ 2", "สาขาที่ 3"])
        month = st.selectbox("เดือนที่สอบ", ["มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน"])
    with col2:
        subject = st.selectbox("วิชาที่สอน", ["คณิตศาสตร์", "วิทยาศาสตร์", "ภาษาอังกฤษ"])
        teacher = st.text_input("ชื่อครูผู้บันทึก")

    st.divider()
    
    student_name = st.text_input("ชื่อ-นามสกุล นักเรียน")
    
    c1, c2, c3 = st.columns(3)
    with c1: s1 = st.number_input("คะแนนด้านที่ 1", 0, 100)
    with c2: s2 = st.number_input("คะแนนด้านที่ 2", 0, 100)
    with c3: s3 = st.number_input("คะแนนด้านที่ 3", 0, 100)

    submitted = st.form_submit_button("🚀 บันทึกข้อมูลลงระบบกลาง")

    if submitted:
        if student_name and teacher:
            try:
                row_data = [
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    branch, month, subject, student_name, s1, s2, s3, teacher
                ]
                worksheet.append_row(row_data)
                st.success(f"บันทึกคะแนนของ {student_name} สำเร็จเรียบร้อย!")
                st.balloons()
            except Exception as e:
                st.error(f"เกิดข้อผิดพลาด: {e}")
        else:
            st.warning("กรุณากรอก ชื่อนักเรียน และ ชื่อครูผู้บันทึก ให้ครบถ้วนครับ")

# --- VIEW DATA ---
if st.checkbox("🔍 ดูฐานข้อมูลปัจจุบัน"):
    try:
        data = worksheet.get_all_records()
        if data:
            st.dataframe(pd.DataFrame(data))
        else:
            st.info("ยังไม่มีข้อมูลในระบบครับ")
    except Exception as e:
        st.error(f"ไม่สามารถดึงข้อมูลมาแสดงได้: {e}")