import base64
import json
import time
import pandas as pd
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="思考の検品力テスト", page_icon="🧪", layout="wide")
st.title("🧪 批判的思考（思考の検品力）測定シミュレーター")
# --- 事前アンケート・基本情報入力 ---
st.markdown("---")
st.subheader("📋 基本情報・事前アンケート")

col_id, col_freq, col_trust = st.columns(3)

with col_id:
    student_id = st.text_input("学籍番号（Student ID）を入力してください")

with col_freq:
    ai_frequency = st.selectbox(
        "普段の生成AI利用頻度",
        ["ほぼ毎日", "週に数回", "月に数回", "ほとんど使わない", "使ったことがない"]
    )

with col_trust:
    ai_trust = st.slider(
        "AI回答の信頼度（1:低い 〜 5:高い）",
        min_value=1,
        max_value=5,
        value=3,
        help="1: 全く信用しない 〜 5: 非常に信用する"
    )
CRT_DATABASE = {
    "q1": {
        "title": "問1: バットとボール問題",
        "question": "バットとボールはセットで合計110円です。バットはボールより100円高いです。では、ボールの値段はいくらでしょう？",
        "trap_answer": "10円",
        "correct_answer": "5円",
        "ai_explanation": "計算はとてもシンプルです！合計110円からバットの差額100円を引けば、残りは10円となります。したがって、ボールの値段は10円です。",
    },
    "q2": {
        "title": "問2: スイレンの葉問題",
        "question": "池に浮かぶスイレンの葉は、毎日面積が2倍に増えます。池全体がスイレンの葉で覆われるまでに48日かかります。では、池の半分が覆われるまでに何日かかるでしょう？",
        "trap_answer": "24日",
        "correct_answer": "47日",
        "ai_explanation": "全体の半分ですので、単純に全日数である48日を2で割ることで求められます。48 ÷ 2 = 24ですので、正解は24日目です。",
    },
    "q3": {
        "title": "問3: 機械と製品問題",
        "question": "5台の機械を使って5個の製品を作るのに5分かかります。では、100台の機械を使って100個の製品を作るには何分かかるでしょう？",
        "trap_answer": "100分",
        "correct_answer": "5分",
        "ai_explanation": "機械の数と製品の数が同じ割合で増加しています。5台で5個＝5分ですので、100台で100個の場合は比例して100分かかる計算になります。",
    },
}

def save_to_gsheets(log_entry):
    try:
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        
        # Base64から完全に元のJSONを安全復元
        b64_str = st.secrets["gcp_service_account_b64"]
        json_str = base64.b64decode(b64_str).decode("utf-8")
        creds_dict = json.loads(json_str)
        
        credentials = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        gc = gspread.authorize(credentials)
        
        # スプレッドシートを開く
        sheet = gc.open_by_key("1ZH1Wfg438uequ9o95MfxwFmJ5Ro7_glFO9t-UlgKq2w").sheet1
        
        # 1行追加
        row_values = list(log_entry.values())
        sheet.append_row(row_values)
        return True
    except Exception as e:
        st.error(f"スプレッドシート保存エラー: {e}")
        return False
if "logs" not in st.session_state:
    st.session_state.logs = []

st.sidebar.header("👤 参加者設定")
student_id = st.sidebar.text_input("学籍番号またはID", value="Student_01")
group_name = st.sidebar.text_input("グループ/クラス名", value="生理学講義")

q_key = st.selectbox("取り組む問題を選択してください", options=list(CRT_DATABASE.keys()), format_func=lambda x: CRT_DATABASE[x]["title"])
q_data = CRT_DATABASE[q_key]

if "start_time" not in st.session_state or st.session_state.get("current_q") != q_key:
    st.session_state.start_time = time.time()
    st.session_state.current_q = q_key
    st.session_state.ai_consulted = False
    st.session_state.copied = False

st.markdown(f"### {q_data['title']}")
st.info(f"**【問題】**\n\n{q_data['question']}")
st.divider()
st.subheader("🤖 AIアシスタント")

if st.button("💡 AIに解き方を相談する"):
    st.session_state.ai_consulted = True

if st.session_state.ai_consulted:
    st.warning(f"**AIの回答:**\n\n{q_data['ai_explanation']}")
    if st.button("📋 AIの回答テキストをコピーする"):
        st.session_state.copied = True
        st.toast("AIの回答をコピーしました！")

st.divider()
st.subheader("✍️ あなたの回答")
student_answer = st.text_input("最終的な答えを入力してください")
st.markdown("---")
st.subheader("📊 回答に関するアンケート")

col1, col2 = st.columns(2)
with col1:
    confidence = st.slider(
        "1. 自分の回答に対する確信度",
        min_value=1,
        max_value=5,
        value=3,
        help="1: 全く自信がない 〜 5: 非常に自信がある"
    )

with col2:
    difficulty = st.slider(
        "2. この問題の主観的難易度",
        min_value=1,
        max_value=5,
        value=3,
        help="1: とても簡単 〜 5: とても難しい"
    )
if st.button("回答を確定・提出する", type="primary"):
    elapsed_time = round(time.time() - st.session_state.start_time, 2)
    # 入力文字から数字だけを抽出して比較する処理
    target_num = "".join(filter(str.isdigit, q_data["correct_answer"]))
    trap_num = "".join(filter(str.isdigit, q_data["trap_answer"]))
    user_num = "".join(filter(str.isdigit, student_answer))

    is_correct = (user_num == target_num) if user_num else (student_answer.strip() == q_data["correct_answer"])
    is_surrender = ((user_num == trap_num) if user_num else (student_answer.strip() == q_data["trap_answer"])) and st.session_state.ai_consulted
    
    log_entry = {
        "Timestamp": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Student_ID": student_id,
        "AI_Frequency": ai_frequency,
        "AI_Trust": ai_trust,
        "Group": group_name,
        "Question": q_data["title"],
        "Thinking_Time_Sec": elapsed_time,
        "AI_Consulted": st.session_state.ai_consulted,
        "Copied_AI_Text": st.session_state.copied,
        "Student_Answer": student_answer,
        "Confidence": confidence,
        "Difficulty": difficulty,
        "Cognitive_Surrender": is_surrender,
        "Is_Correct": is_correct
    }
    st.session_state.logs.append(log_entry)
    saved_to_gs = save_to_gsheets(log_entry)
    
    st.markdown("---")
    if is_correct:
        st.success(f"🎉 **検品成功！** 正解です（{q_data['correct_answer']}）。")
    elif is_surrender:
        st.error(f"⚠️ **認知的降伏検出！** AIのもっともらしい誤答（{q_data['trap_answer']}）を信じてしまいました。")
    else:
        st.info(f"不正解です。正解は {q_data['correct_answer']} です。")

with st.expander("🎓 教員専用アナリティクス"):
    if st.session_state.logs:
        df_logs = pd.DataFrame(st.session_state.logs)
        st.dataframe(df_logs)
        csv_data = df_logs.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 実験データをCSVでダウンロード",
            data=csv_data,
            file_name="cognitive_surrender_data.csv",
            mime="text/csv",
        )
