import time
import json
import pandas as pd
import streamlit as st
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="思考の検品力テスト", page_icon="🧪", layout="wide")
st.title("🧪 批判的思考（思考の検品力）測定シミュレーター")

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

def save_to_gsheets(log_data):
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        existing_data = conn.read(ttl=0)
        new_df = pd.DataFrame([log_data])
        updated_df = new_df if existing_data.empty else pd.concat([existing_data, new_df], ignore_index=True)
        conn.update(data=updated_df)
        return True
    except Exception:
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
        "Group": group_name,
        "Question": q_data["title"],
        "Thinking_Time_Sec": elapsed_time,
        "AI_Consulted": st.session_state.ai_consulted,
        "Copied_AI_Text": st.session_state.copied,
        "Student_Answer": student_answer,
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
