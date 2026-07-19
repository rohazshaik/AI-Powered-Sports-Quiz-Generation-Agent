import streamlit as st

st.set_page_config(page_title="Sports Quiz Agent", page_icon="🏆", layout="centered")

from src.database import seed_database
from src.generator import generate_quiz


@st.cache_resource
def load_knowledge_base():
    seed_database()


load_knowledge_base()
st.title("🏆 AI-Powered Sports Quiz Generator")
st.write(
    "Pick a sport and difficulty, and the app will build a grounded quiz from "
    "local facts plus live web snippets."
)

st.sidebar.header("Quiz Settings")
sport_choice = st.sidebar.selectbox(
    "Sport", ["Cricket", "Football", "Badminton", "Tennis", "Basketball"]
)
difficulty_choice = st.sidebar.select_slider(
    "Difficulty", options=["Easy", "Medium", "Hard"]
)
question_count = st.sidebar.slider("Number of questions", 4, 5, 4)

if "quiz_questions" not in st.session_state:
    st.session_state.quiz_questions = []
    st.session_state.quiz_context = ""
    st.session_state.answers_picked = {}

if st.sidebar.button("Generate Quiz", use_container_width=True):
    with st.spinner("Retrieving facts and writing questions..."):
        try:
            questions, context_used = generate_quiz(
                sport_choice, difficulty_choice, question_count
            )
            if not questions:
                st.error("The model reply didn't parse into questions. Try again.")
            else:
                st.session_state.quiz_questions = questions
                st.session_state.quiz_context = context_used
                st.session_state.answers_picked = {}
        except Exception as error:
            st.error(f"Something went wrong: {error}")

if st.session_state.quiz_questions:
    st.subheader(f"{sport_choice} Quiz — {difficulty_choice}")

    for i, q in enumerate(st.session_state.quiz_questions):
        st.markdown(f"**Q{i + 1}. {q['question']}**")

        picked = st.radio(
            label="Choose an answer",
            options=list(q["options"].keys()),
            format_func=lambda letter: f"{letter}) {q['options'][letter]}",
            key=f"question_{i}",
            index=None,
            label_visibility="collapsed",
        )

        if picked:
            st.session_state.answers_picked[i] = picked
            if picked == q["correct"]:
                st.success(f"Correct! {q['explanation']}")
            else:
                correct_option = q["options"][q["correct"]]
                st.error(
                    f"Not quite. Correct answer: {q['correct']}) {correct_option}\n\n"
                    f"{q['explanation']}"
                )
        st.divider()

    with st.expander("🔍 See the context this quiz was grounded in"):
        st.code(st.session_state.quiz_context, language="markdown")
else:
    st.info("Set your options in the sidebar and click **Generate Quiz** to start.")
