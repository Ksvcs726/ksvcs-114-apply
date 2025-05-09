
import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import datetime
import pytz
from collections import Counter
import streamlit.components.v1 as components

def show_alert(msg):
    components.html(f"<script>alert('{msg}')</script>", height=0)

# === 設定報名截止時間 ===
tz = pytz.timezone("Asia/Taipei")
報名截止時間 = datetime.datetime(2025, 5, 19, 12, 0, 0, tzinfo=tz)

# === Google Sheets 設定 ===
creds_dict = st.secrets["GOOGLE_CREDENTIALS"]
CREDS = Credentials.from_service_account_info(creds_dict, scopes=[
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
])
CLIENT = gspread.authorize(CREDS)

# Google Sheet URL
表單_URL = 'https://docs.google.com/spreadsheets/d/1RrOvJ_UeP5xu2-l-WJwDySn9d786E5P0hsv_XFq9ovg'
報名紀錄_URL = 'https://docs.google.com/spreadsheets/d/1awfvTvLPkyZM3sGL41sflHtO7LgTkva-lkWx-2rUu7k'

表單 = CLIENT.open_by_url(表單_URL)
報名紀錄 = CLIENT.open_by_url(報名紀錄_URL)
報名工作表 = 報名紀錄.sheet1

df1 = pd.DataFrame(表單.worksheet('工作表1').get_all_records())
df3 = pd.DataFrame(表單.worksheet('工作表3').get_all_records())
df4 = pd.DataFrame(表單.worksheet('工作表4').get_all_records())

群別選項 = sorted(df3["統測報考群(類)別"].unique())

st.title("📋 高雄高商114學年度 甄選入學第一階段報名系統")
tab1, tab2 = st.tabs(["我要報名", "查詢報名紀錄"])

with tab1:
    if "已驗證" not in st.session_state:
        st.session_state["已驗證"] = False

    if not st.session_state["已驗證"]:
        with st.form("verify_form"):
            col1, col2 = st.columns(2)
            with col1:
                exam_id = st.text_input("統測報名序號")
                id_number = st.text_input("身分證字號")
            with col2:
                name = st.text_input("考生姓名")
            verify = st.form_submit_button("✅ 開始報名")

        if verify:
            match = df4[
                (df4["統測報名序號"].str.strip() == exam_id.strip()) &
                (df4["考生姓名"].str.strip() == name.strip()) &
                (df4["身分證統一編號"].str.strip().str.upper() == id_number.strip().upper())
            ]
            if match.empty:
                show_alert("❌ 查無此考生資料，請確認輸入正確")
                st.stop()
            else:
                st.session_state["已驗證"] = True
                st.session_state["exam_id"] = exam_id.strip()
                st.session_state["name"] = name.strip()
                st.session_state["id_number"] = id_number.strip().upper()
                st.success("✅ 驗證成功，請繼續填寫表單")
                st.rerun()

    if st.session_state["已驗證"]:
        with st.form("apply_form"):
            群別 = st.selectbox("統測報考群別", 群別選項)
            st.markdown("請依序填寫最多 6 組志願校系代碼：")
            志願1 = st.text_input("第1組校系代碼")
            志願2 = st.text_input("第2組校系代碼")
            志願3 = st.text_input("第3組校系代碼")
            志願4 = st.text_input("第4組校系代碼")
            志願5 = st.text_input("第5組校系代碼")
            志願6 = st.text_input("第6組校系代碼")
            submitted = st.form_submit_button("📨 送出報名")

        if submitted:
            now = datetime.datetime.now(tz)
            if now > 報名截止時間:
                st.error("❌ 報名已截止，無法提交。")
                st.stop()

            填寫代碼 = [c.strip() for c in [志願1, 志願2, 志願3, 志願4, 志願5, 志願6] if c.strip()]
            row = [
                st.session_state["exam_id"],
                st.session_state["name"],
                st.session_state["id_number"],
                群別
            ] + 填寫代碼 + [""] * (6 - len(填寫代碼)) + [now.strftime("%Y-%m-%d %H:%M:%S")]

            try:
                報名工作表.append_row(row)
                st.success("✅ 報名成功，資料已儲存！")
                st.dataframe(pd.DataFrame([row], columns=[
                    "統測報名序號", "姓名", "身分證字號", "群別",
                    "志願1", "志願2", "志願3", "志願4", "志願5", "志願6", "報名時間"
                ]))
            except Exception as e:
                st.error(f"❌ 寫入失敗：{e}")

with tab2:
    st.subheader("🔍 查詢報名紀錄")
    查序號 = st.text_input("請輸入統測報名序號", key="查序號")
    查身分 = st.text_input("請輸入身分證字號", key="查身分")

    if st.button("查詢"):
        try:
            資料 = 報名工作表.get_all_values()
            原始標題 = 資料[0]
            counts = Counter(原始標題)
            標題 = []
            seen = {}
            for name in 原始標題:
                if counts[name] == 1:
                    標題.append(name)
                else:
                    i = seen.get(name, 1)
                    標題.append(f"{name}_{i}")
                    seen[name] = i + 1
            df查 = pd.DataFrame(資料[1:], columns=標題)
            結果 = df查[
                (df查["統測報名序號"] == 查序號) &
                (df查["身分證字號"] == 查身分)
            ]
            if 結果.empty:
                st.info("查無資料")
            else:
                st.dataframe(結果)
        except Exception as e:
            st.error(f"查詢錯誤：{e}")
