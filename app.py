import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
import os

# --- CONFIGURATION ---
st.set_page_config(page_title="ระบบบันทึกคะแนนแบบทดสอบติวเข้าม.1 กรุงเทพ", layout="wide") 

# 🔗 ลิงก์ Google Sheets ของคุณบาส
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1ny5m5Yq4V269FdZemV105cDPeVUcp9sGjOyVAbbnA0Q/edit"

# --- 1. การเชื่อมต่อฐานข้อมูล ---
@st.cache_resource
def get_gspread_client():
    try:
        if "gcp_service_account" in st.secrets:
            # ดึงกุญแจจาก Streamlit Secrets (สำหรับออนไลน์)
            return gspread.service_account_from_dict(dict(st.secrets["gcp_service_account"]))
        else:
            # ดึงจากไฟล์ creds.json ในเครื่อง (สำหรับทดสอบในคอม)
            return gspread.service_account(filename="creds.json")
    except Exception as e:
        st.error(f"🚨 ไม่สามารถเชื่อมต่อกับ Google API ได้: {e}")
        return None

gc = get_gspread_client()

if gc:
    try:
        sh = gc.open_by_url(SPREADSHEET_URL)
        worksheet_data = sh.worksheet("Sheet1")     # หน้าสำหรับบันทึกคะแนน
        worksheet_list = sh.worksheet("StudentList") # หน้าสำหรับรายชื่อและสาขา
        
        # ดึงข้อมูลนักเรียนและสาขามาเตรียมไว้
        # คอลัมน์ A=Name, B=Branch ตามที่คุณบาสทำไว้
        master_data = worksheet_list.get_all_records()
        df_master = pd.DataFrame(master_data)
        df_master['Name'] = df_master['Name'].astype(str).str.strip()
        df_master['Branch'] = df_master['Branch'].astype(str).str.strip()
    except Exception as e:
        st.error(f"🚨 หาแผ่นงาน (Tab) ไม่เจอ: {e}")
        st.stop()
else:
    st.stop()

# --- UI INTERFACE ---
st.title("🎓 ระบบจัดการคะแนนสอบกลาง (Update Mode)")
st.markdown("---")

# แบ่งหน้าจอเป็น 2 ฝั่ง: [ฝั่งกรอกข้อมูล] และ [ฝั่งโชว์ตารางรวม]
col_form, col_table = st.columns([1, 1.3])

with col_form:
    st.subheader("📝 บันทึก/แก้ไขคะแนน")
    
    # ดึงรายชื่อสาขาที่มีอยู่จริงใน Sheets (บางนา, รามคำแหง, พาราไดซ์ พาร์ค) มาโชว์
    all_branches = sorted(df_master['Branch'].unique().tolist())
    selected_branch = st.selectbox("1. เลือกสาขา", ["-- โปรดเลือกสาขา --"] + all_branches)
    
    # กรองรายชื่อเด็กตามสาขาที่เลือก
    if selected_branch != "-- โปรดเลือกสาขา --":
        names_in_branch = df_master[df_master['Branch'] == selected_branch]['Name'].tolist()
    else:
        names_in_branch = []
        
    student_name = st.selectbox("2. เลือกชื่อนักเรียน", ["-- โปรดเลือกรายชื่อ --"] + names_in_branch)

    # ฟอร์มกรอกข้อมูลคะแนน
    with st.form("score_entry_form", clear_on_submit=True):
        st.write(f"📌 กำลังบันทึกข้อมูลของ: **{student_name if student_name != '-- โปรดเลือกรายชื่อ --' else '-'}**")
        
        c1, c2 = st.columns(2)
        with c1:
            subject = st.selectbox("วิชา", ["คณิตศาสตร์", "วิทยาศาสตร์", "ภาษาอังกฤษ"])
        with c2:
            month = st.selectbox("เดือนที่สอบ", ["มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน"])
        
        st.divider()
        st.write("📊 **คะแนนสอบ 3 ด้าน**")
        s1 = st.number_input("ด้านที่ 1 (ความรู้)", 0, 100, step=1)
        s2 = st.number_input("ด้านที่ 2 (ทักษะ)", 0, 100, step=1)
        s3 = st.number_input("ด้านที่ 3 (วิเคราะห์)", 0, 100, step=1)
        
        submitted = st.form_submit_button("🚀 บันทึกข้อมูลลง Google Sheets")

        if submitted:
            if student_name != "-- โปรดเลือกรายชื่อ --":
                try:
                    # ค้นหาแถวของเด็กคนนั้นใน Sheet1 (คอลัมน์ A)
                    cell = worksheet_data.find(student_name)
                    row_idx = cell.row
                    
                    # เตรียมข้อมูลอัปเดตลงคอลัมน์ B ถึง G
                    # [Branch, Month, Subject, Score1, Score2, Score3]
                    update_row = [[selected_branch, month, subject, s1, s2, s3]]
                    
                    # สั่งอัปเดตช่วงเซลล์ B{row}:G{row}
                    worksheet_data.update(f"B{row_idx}:G{row_idx}", update_row)
                    
                    st.success(f"✅ อัปเดตคะแนนของ '{student_name}' เรียบร้อยแล้วที่แถว {row_idx}!")
                    st.balloons()
                    # รีเฟรชหน้าจอเพื่ออัปเดตตารางฝั่งขวา
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ ไม่พบชื่อนักเรียนในแผ่นงาน 'Sheet1' หรือเกิดข้อผิดพลาด: {e}")
            else:
                st.warning("⚠️ กรุณาเลือกชื่อนักเรียนก่อนกดบันทึก")

with col_table:
    st.subheader("🔍 ตารางคะแนนรวม (Sheet1)")
    try:
        # ดึงข้อมูลจาก Sheet1 มาแสดงผลแบบ Real-time
        all_scores = worksheet_data.get_all_records()
        if all_scores:
            df_display = pd.DataFrame(all_scores)
            st.dataframe(df_display, use_container_width=True, height=650)
            
            # ปุ่มดาวน์โหลดข้อมูลเป็น CSV เผื่อคุณบาสต้องเอาไปทำรายงานต่อ
            csv = df_display.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label="📥 ดาวน์โหลดข้อมูลเป็น CSV",
                data=csv,
                file_name=f"scores_summary_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
            )
        else:
            st.info("ยังไม่มีข้อมูลใน Sheet1 (ตรวจสอบว่าพิมพ์ชื่อเด็กในคอลัมน์ A หรือยัง)")
    except Exception as e:
        st.write("ระบบกำลังเตรียมข้อมูล...")