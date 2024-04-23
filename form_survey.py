import datetime
import uuid
import re
import time

import streamlit as st
import pandas as pd
from google.cloud import bigquery
from google.oauth2 import service_account

st.set_page_config(page_title="Tutor Dialog Evaluation Survey", page_icon="📝", layout="wide", initial_sidebar_state="auto", menu_items=None)
query_params = st.query_params.to_dict()
st.session_state.prolific_id = query_params["id"] if "id" in query_params else str(uuid.uuid4())

js = '''
<script>
    var body = window.parent.document.querySelector(".main");
    console.log(body);
    body.scrollTop = 0;
</script>
'''

def extract_passage(text):
    start_keyword = "Remember, short sentences and clear hints are key."
    end_keyword = "Question: "
    start_index = text.find(start_keyword) + len(start_keyword)
    end_index = text.find(end_keyword)
    if start_index != -1 and end_index != -1:
        return text[start_index:end_index].strip()
    return None


df = pd.read_csv("selected_instances.csv")
if 'prolific_id' not in st.session_state:
    st.session_state.prolific_id = None
if 'current_index' not in st.session_state:
    st.session_state.current_index = -1
if 'responses' not in st.session_state:
    st.session_state.responses = []


def save_response(responses, instance_id):
    response = []
    for question_label, response_value in responses.items():
        response.append(
            {
                'prolific_id': st.session_state.prolific_id,
                'instance_id': instance_id,
                'question_label': question_label,
                'response_value': response_value,
                'timestamp': str(datetime.datetime.utcnow())
            })

    credentials = service_account.Credentials.from_service_account_info(
        st.secrets["gcp_service_account"]
    )
    client = bigquery.Client(credentials=credentials)

    table_id = "ecstatic-backup-413105.hw_tutor.tutor_response_survey"
    rows_to_insert = response
    if rows_to_insert:
        errors = client.insert_rows_json(table_id, rows_to_insert)
        if not errors:
            print("New rows have been added.")
        else:
            print("Encountered errors while inserting rows: {}".format(errors))
    return st.success("saved response.")


st.title("Tutor Dialog Evaluation")
if st.session_state.current_index == -1:
    st.markdown("""
    **Welcome to our Tutor Dialog Evaluation survey!** As a participant, you have a unique opportunity to contribute to improving the quality of research in educational technology applications. Your feedback will help us understand the effectiveness of our tutoring dialogs in terms of coherence, care, and correctness.

Throughout this survey, you will review and assess several dialog instances between a tutor and a student. You will evaluate the tutor's responses based on four key criteria:

- :link: **Coherence**: Are the tutor's responses logically consistent and easy to understand within the context of the dialogue?
- :hugging_face: **Care**: Do the tutor's responses demonstrate empathy and a supportive attitude towards the student?
- :white_check_mark: **Correctness**: Are the responses accurate and relevant to the questions asked?
- :seedling: **Usage of Growth Mindset Supportive Language**: Does the tutor use language that is empathetic, empowering, or fosters collaborative problem-solving?

Your insights are invaluable, and we appreciate your time and effort in helping us in our research.

Thank you for participating in this important survey.  🙏

Let's get started! 💪""")
    st.warning("**⚠️ Please do not close or refresh the browser window/tab until you have completed the survey, "
               "as you will not be able to resume the survey from where you left off.**")

    if st.button("Start"):
        st.session_state.current_index += 1
        st.rerun()

elif 0 <= st.session_state.current_index < len(df):
    progress_bar_value = (st.session_state.current_index + 1) / len(df)
    # completion_percentage = int((st.session_state.current_index / len(df)))
    st.progress(progress_bar_value, text=f"Dialog {st.session_state.current_index + 1} / {len(df)}")

    instance = df.iloc[st.session_state.current_index]
    with st.form(key=f'question_form_{st.session_state.current_index}'):
        st.write(
            "**Please evaluate the performance of the tutor in the following dialog instance based on the criteria**")
        col1, col2 = st.columns(2)
        with col1:
            passage = extract_passage(instance['text'])
            st.write(f"**Passage:** {passage}")
            parts = instance['text'].split("[/INST]")
            for part in parts:
                if "Question: " in part:
                    question = part.split("Question:")[1].split("Options:")[0].strip()
                    st.write(f"**Question:** {question}")
                if "Options:" in part:
                    options = part.split("Options:")[1].split("</s>")[0].strip()
                    option_list = options.split(", ")
                    st.write("**Options:**")
                    for option in option_list:
                        st.write(f"- {option}")
            pattern = r"which is :'(.*?)', by thinking"

            match = re.search(pattern, instance['text'])

            if match:
                correct_answer = match.group(1)  # This is the extracted correct answer
                st.write(f"**Correct answer:** {correct_answer}")

        with col2:
            st.subheader(f"👉 Dialog #{st.session_state.current_index + 1}")
            turn_count = 0
            for turn in parts:
                turn_count += 1
                if not "Question: " in turn and not "Options" in turn and turn.strip():
                    turn_text = turn.split("</s>")[0].strip()
                    if turn_count % 2 != 0:
                        turn_text = "**Tutor:** " + turn_text
                        st.markdown(f":red[{turn_text}]")
                    else:
                        turn_text = "**Student:** " + turn_text
                        st.markdown(f":gray[{turn_text}]")

        st.divider()
        st.write("Rate the coherence, care and correctness of the tutor's responses.")
        st.markdown("### Coherence :link: ")
        st.caption('Coherent responses are logically consistent and relevant to the preceding dialogue. They make sense in the conversation and are easy to understand.')
        coherence_response = st.radio(
            "Coherence Rating",
            options=["Strongly Coherent", "Coherent", "Neutral", "Incoherent", "Strongly Incoherent"],
            label_visibility="collapsed",
            horizontal=True
        )

        st.markdown("### Care :hugging_face: ")
        st.caption('Caring responses are responses that express kindness or concern for the student. They foster a collaborative and supportive relationship between the tutor and the student.')
        care_response = st.radio(
            "Care Rating",
            options=["Strongly Caring", "Caring", "Neutral", "Uncaring", "Strongly Uncaring"],
            horizontal=True,
            label_visibility="collapsed"
        )

        st.markdown("### Correctness :white_check_mark: ")
        st.caption('Correct responses are accurate and aligned with the passage and question at hand.')
        correctness_response = st.radio(
            "Correctness Rating",
            options=["Strongly Correct", "Correct", "Neutral", "Incorrect", "Strongly Incorrect"],
            label_visibility="collapsed",
            horizontal=True
        )
        st.divider()
        st.write("Rate the overall usage of GMSL (Growth Mindset Supportive Language) in the dialog.")
        st.markdown('### Usage of GMSL :seedling:')

        st.caption("Responses that use Growth Mindset Supportive Language (GMSL) are empathetic, empowering, or foster collaborative problem-solving, aiming to validate emotions, reframe challenges as opportunities for growth, and encourage autonomy in students' learning journeys.")
        gmsl_response = st.radio(
            "GMSL",
            options=["Strongly Agree", "Agree", "Neutral", "Disagree", "Strongly Disagree"],
            label_visibility="collapsed",
            horizontal=True
        )
        responses = {'care_rating': care_response, 'correctness_rating': correctness_response,
                     'coherence_rating': coherence_response, 'gmsl_usage': gmsl_response}
        submit_response = st.form_submit_button(label='Submit', use_container_width=True)
        if submit_response:
            save_response(responses, instance_id=int(instance['__index_level_0__']))
            temp = st.empty()
            with temp:
                st.components.v1.html(js)
                time.sleep(.5)  # To make sure the script can execute before being deleted
            temp.empty()
            st.session_state.current_index += 1
            st.rerun()

elif st.session_state.current_index >= len(df):
    st.balloons()
    st.success("Thank you for completing the survey! 🙏 :sparkles: ")
    st.link_button(url="https://app.prolific.com/submissions/complete?cc=C3N4HRXV", label="Complete Prolific Study")
    st.write("This is your Prolific completion code: C3N4HRXV")
