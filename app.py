
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import datetime
import pytz
import re

# --- Google Sheets 連線 ---
creds_dict = st.secrets["GOOGLE_CREDENTIALS"]
CREDS = Credentials.from_service_account_info(creds_dict, scopes=[
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
])
CLIENT = gspread.authorize(CREDS)

# === 資料來源 ===
表單_URL = 'https://docs.google.com/spreadsheets/d/1RrOvJ_UeP5xu2-l-WJwDySn9d786E5P0hsv_XFq9ovg/edit?usp=sharing'
報名紀錄_URL = 'https://docs.google.com/spreadsheets/d/1awfvTvLPkyZM3sGL41sflHtO7LgTkva-lkWx-2rUu7k/edit?usp=drive_link'

工作表1 = CLIENT.open_by_url(表單_URL).worksheet('工作表1')  # 校系資料
工作表2 = CLIENT.open_by_url(表單_URL).worksheet('工作表2')  # 校數限制
工作表3 = CLIENT.open_by_url(表單_URL).worksheet('工作表3')  # 群別可報名對照
工作表4 = CLIENT.open_by_url(表單_URL).worksheet('工作表4')  # 考生基本資料

try:
    報名工作表 = CLIENT.open_by_url(報名紀錄_URL).sheet1
except Exception as e:
    show_alert("❌ 無法開啟報名紀錄表單，請確認網址正確並已分享給服務帳戶！")
    st.stop()


df1 = pd.DataFrame(工作表1.get_all_records())
df2 = pd.DataFrame(工作表2.get_all_records())
df3 = pd.DataFrame(工作表3.get_all_records())
df4 = pd.DataFrame(工作表4.get_all_records())

群別選項 = sorted(df3["統測報考群(類)別"].unique())

st.title("📋 高雄高商114學年度 第一階段甄選入學報名系統")

tab1, tab2 = st.tabs(["我要報名", "查詢報名紀錄"])

with tab1:
    st.subheader("🔐 請先進行身份驗證")

    with st.form("身份驗證"):
        col1, col2 = st.columns(2)
        with col1:
            st.session_state['exam_id'] = st.text_input("統測報名序號")
            st.session_state['id_number'] = st.text_input("身分證字號")
        with col2:
            st.session_state['name'] = st.text_input("考生姓名")
        verify = st.form_submit_button("✅ 開始報名")

    if verify:
        if not re.match(r"^[A-Z][0-9]{9}$", st.session_state['id_number'].upper()):
            st.error("⚠️ 身分證格式錯誤，應為 1 大寫英文字 + 9 碼數字")
        else:
            match = df4[
                (df4["統測報名序號"].str.strip() == st.session_state['exam_id'].strip()) &
                (df4["考生姓名"].str.strip() == st.session_state['name'].strip()) &
                (df4["身分證統一編號"].str.strip().str.upper() == st.session_state['id_number'].strip().upper())
            ]
            if match.empty:
                st.error("❌ 查無此考生資料，請確認輸入正確")
            else:
                st.session_state["已驗證"] = True
        st.session_state["st.session_state['exam_id']"] = st.session_state['exam_id'].strip()
        st.session_state["st.session_state['name']"] = st.session_state['name'].strip()
        st.session_state["st.session_state['id_number']"] = st.session_state['id_number'].strip().upper()
        st.success("✅ 身份驗證成功，請繼續填寫報名資料")

                if "已驗證" in st.session_state and st.session_state["已驗證"]:
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
                        志願清單 = [志願1.strip(), 志願2.strip(), 志願3.strip(),
                                 志願4.strip(), 志願5.strip(), 志願6.strip()]
                        錯誤訊息 = []
                        有效志願 = [x for x in 志願清單 if x]

                        可報名群列 = df3[df3["統測報考群(類)別"] == 群別]
                        可報名群別 = []
                        if not 可報名群列.empty:
                            可報名群別 = 可報名群列.iloc[0]["可報名的招生群(類)別"].split("、")

                        不合法代碼 = []
                        學校代碼統計 = {}
                        for code in 有效志願:
                            if code not in df1["校系代碼"].values:
                                不合法代碼.append(code)
                                continue
                            招生群 = df1[df1["校系代碼"] == code].iloc[0]["招生群(類)別"]
                            if 招生群 not in 可報名群別:
                                不合法代碼.append(code)

                            school_code = code[:3]
                            學校代碼統計[school_code] = 學校代碼統計.get(school_code, 0) + 1

                        超出校數 = []
                        for s_code, cnt in 學校代碼統計.items():
                            if s_code in df2["學校代碼"].values:
                                限制 = int(df2[df2["學校代碼"] == s_code]["可報名之系科組學程數"].values[0])
                                if cnt > 限制:
                                    超出校數.append(f"{s_code}（限{限制}組，填{cnt}組）")

                        所有資料 = 報名工作表.get_all_values()
                        已有_df = pd.DataFrame(所有資料[1:], columns=所有資料[0])
                        重複 = not 已有_df[
                            (已有_df["統測報名序號"] == st.session_state['exam_id']) &
                            (已有_df["身分證字號"] == st.session_state['id_number'])
                        ].empty

                        if 不合法代碼:
                            st.error(f"以下代碼不符規定或無法報名：{', '.join(不合法代碼)}")
                        elif 超出校數:
                            st.error(f"以下學校代碼超出可報名上限：{'；'.join(超出校數)}")
                        elif 重複:
                            st.warning("⚠️ 您已經填寫過報名，請勿重複提交。")
                        else:
                            tz = pytz.timezone("Asia/Taipei")
                            now = datetime.datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")

                            row = [st.session_state['exam_id'], st.session_state['name'], st.session_state['id_number'], 群別,
                                   志願1, 志願2, 志願3, 志願4, 志願5, 志願6, now]
                            報名工作表.append_row(row)
                            st.success("✅ 報名成功！以下為您填寫的內容：")

                            df_show = pd.DataFrame([row], columns=[
                                "統測報名序號", "姓名", "身分證字號", "群別",
                                "第1組校系代碼", "第2組校系代碼", "第3組校系代碼",
                                "第4組校系代碼", "第5組校系代碼", "第6組校系代碼",
                                "填寫時間"
                            ])
                            st.dataframe(df_show)

with tab2:
    st.subheader("🔍 查詢報名紀錄")
    查序號 = st.text_input("請輸入統測報名序號", key="查序號")
    查身分 = st.text_input("請輸入身分證字號", key="查身分")

    if st.button("查詢"):
        try:
            資料 = 報名工作表.get_all_values()
            標題原始 = 資料[0]
            from collections import Counter
            counts = Counter(標題原始)
            標題 = []
            seen = {}
            for st.session_state['name'] in 標題原始:
                if counts[st.session_state['name']] == 1:
                    標題.append(st.session_state['name'])
                else:
                    i = seen.get(st.session_state['name'], 1)
                    標題.append(f"{st.session_state['name']}_{i}")
                    seen[st.session_state['name']] = i + 1
            df查 = pd.DataFrame(資料[1:], columns=標題)
            結果 = df查[
                (df查["統測報名序號"] == 查序號) &
                (df查["身分證字號"] == 查身分)
            ]
            if 結果.empty:
                st.info("查無資料，請確認輸入正確。")
            else:
                st.success("查詢成功，以下是您填寫的資料：")
                st.dataframe(結果)
        except Exception as e:
            st.error(f"查詢發生錯誤：{e}")
