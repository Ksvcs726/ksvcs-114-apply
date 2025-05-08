
import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import datetime
import json

# 從 Streamlit secrets 讀取 Google 認證資訊
creds_dict = st.secrets["GOOGLE_CREDENTIALS"]
CREDS = Credentials.from_service_account_info(creds_dict, scopes=[
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
])
CLIENT = gspread.authorize(CREDS)

# 校系資料來源
校系表單_URL = 'https://docs.google.com/spreadsheets/d/1RrOvJ_UeP5xu2-l-WJwDySn9d786E5P0hsv_XFq9ovg/edit?usp=sharing'
校系工作表 = CLIENT.open_by_url(校系表單_URL).worksheet('工作表1')
raw = 校系工作表.get_all_values()
df = pd.DataFrame(raw[1:], columns=raw[0])
群別選項 = sorted(df['欲報名之群(類)別'].unique())

# 儲存報名表單
報名表單_URL = 'https://docs.google.com/spreadsheets/d/1awfvTvLPkyZM3sGL41sflHtO7LgTkva-lkWx-2rUu7k/edit?usp=drive_link'
報名工作表 = CLIENT.open_by_url(報名表單_URL).sheet1

st.title("📋 高雄高商114學年度 第一階段甄選入學報名系統")

tab1, tab2 = st.tabs(["我要報名", "查詢報名紀錄"])

with tab1:
    with st.form("apply_form"):
        col1, col2 = st.columns(2)
        with col1:
            統測報名序號 = st.text_input("統測報名序號")
            身分證字號 = st.text_input("身分證字號")
        with col2:
            姓名 = st.text_input("姓名")
            群別 = st.selectbox("欲報名之群(類)別", 群別選項)

        st.markdown("請依序填寫最多6組志願校系代碼：")
        志願1 = st.text_input("第1志願")
        志願2 = st.text_input("第2志願")
        志願3 = st.text_input("第3志願")
        志願4 = st.text_input("第4志願")
        志願5 = st.text_input("第5志願")
        志願6 = st.text_input("第6志願")

        submitted = st.form_submit_button("✅ 送出報名")

        if submitted:
            合法代碼 = df[df['欲報名之群(類)別'] == 群別]['校系代碼'].tolist()
            志願清單 = [志願1, 志願2, 志願3, 志願4, 志願5, 志願6]
            填寫代碼 = [c.strip() for c in 志願清單 if c.strip()]
            錯誤代碼 = [c for c in 填寫代碼 if c not in 合法代碼]

            所有資料 = 報名工作表.get_all_values()
            已有_df = pd.DataFrame(所有資料[1:], columns=所有資料[0])
            重複 = not 已有_df[(已有_df["統測報名序號"] == 統測報名序號) & (已有_df["身分證字號"] == 身分證字號)].empty

            if 錯誤代碼:
                st.error(f"以下校系代碼不屬於「{群別}」：{', '.join(錯誤代碼)}")
            elif 重複:
                st.warning("⚠️ 您已經完成報名，請勿重複填寫。")
            else:
                now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                row = [統測報名序號, 姓名, 身分證字號, 群別] + 填寫代碼 + [""] * (6 - len(填寫代碼)) + [now]
                報名工作表.append_row(row)
                st.success("✅ 報名成功！您的資料已儲存。")

with tab2:
    st.subheader("🔍 查詢報名紀錄")
    查序號 = st.text_input("請輸入統測報名序號", key="查序號")
    查身分 = st.text_input("請輸入身分證字號", key="查身分證")
    if st.button("查詢"):
        try:
            資料 = 報名工作表.get_all_values()
            標題, 資料列 = 資料[0], 資料[1:]
            df查 = pd.DataFrame(資料列, columns=標題)
            結果 = df查[(df查["統測報名序號"] == 查序號) & (df查["身分證字號"] == 查身分)]
            if 結果.empty:
                st.info("查無資料，請確認輸入正確。")
            else:
                st.success("查詢成功，以下是您已填寫的資料：")
                st.dataframe(結果)
        except Exception as e:
            st.error(f"查詢發生錯誤：{e}")
