import os
import pickle

import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

# ==========================================
# CONFIGURATION
# ==========================================

load_dotenv()

st.set_page_config(
    page_title="TN Agriculture Schemes",
    page_icon="🌾",
    layout="centered"
)

# ==========================================
# LOAD NETWORKX GRAPH
# ==========================================

@st.cache_resource
def load_graph():

    with open("../data/scheme_graph.pkl", "rb") as file:
        return pickle.load(file)


graph = load_graph()

# ==========================================
# OPENAI CLIENT
# ==========================================

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

# ==========================================
# GRAPH FUNCTIONS
# ==========================================

def find_scheme(question):

    question_lower = question.lower()

    scheme_names = [
        node
        for node, data in graph.nodes(data=True)
        if data.get("type") == "Scheme"
    ]

    matches = [
        scheme
        for scheme in scheme_names
        if scheme.lower() in question_lower
    ]

    if matches:
        return max(matches, key=len)

    return None


def get_scheme_data(scheme):

    data = graph.nodes[scheme]

    result = {
        "scheme": scheme,
        "description": data.get("description", ""),
        "funding": data.get("funding", ""),
        "source": data.get("source", "")
    }

    for target in graph.successors(scheme):

        relationship = graph[scheme][target].get("relationship")

        if relationship == "OFFERED_BY":
            result["department"] = target

        elif relationship == "APPLIES_TO":
            result["beneficiary"] = target

        elif relationship == "PROVIDES_BENEFIT":
            result["benefit"] = target

        elif relationship == "HAS_CRITERIA":

            criteria_data = graph.nodes[target]

            result["eligibility"] = criteria_data.get(
                "description",
                ""
            )

    return result


# ==========================================
# OPENAI ANSWER
# ==========================================

def answer_question(question):

    scheme = find_scheme(question)

    if not scheme:

        return (
            "I couldn't identify a Tamil Nadu Government "
            "Agriculture scheme in your question. "
            "Please mention the scheme name."
        )

    scheme_data = get_scheme_data(scheme)

    context = f"""
Scheme Name:
{scheme_data.get("scheme", "")}

Department:
{scheme_data.get("department", "")}

Beneficiary:
{scheme_data.get("beneficiary", "")}

Benefit:
{scheme_data.get("benefit", "")}

Funding:
{scheme_data.get("funding", "")}

Eligibility:
{scheme_data.get("eligibility", "")}

Description:
{scheme_data.get("description", "")}

Source:
{scheme_data.get("source", "")}
"""

    prompt = f"""
You are a helpful assistant for Tamil Nadu Government
Agriculture schemes.

Answer the user's question using ONLY the information
provided in the NetworkX knowledge graph context.

Do not invent information.

If the requested information is not available,
clearly say that it is not available.

Keep the answer simple and useful.

Knowledge Graph Context:
{context}

User Question:
{question}
"""

    response = client.responses.create(
        model="gpt-5-mini",
        input=prompt
    )

    return response.output_text


# ==========================================
# STREAMLIT UI
# ==========================================

st.title("🌾 Tamil Nadu Agriculture Schemes")

st.caption(
    "Ask questions about Tamil Nadu Government "
    "Agriculture schemes."
)

st.divider()

# ==========================================
# SIDEBAR
# ==========================================

with st.sidebar:

    st.header("📊 Knowledge Graph")

    scheme_count = sum(
        1
        for node, data in graph.nodes(data=True)
        if data.get("type") == "Scheme"
    )

    st.metric(
        "Schemes",
        scheme_count
    )

    st.metric(
        "Graph Nodes",
        graph.number_of_nodes()
    )

    st.metric(
        "Relationships",
        graph.number_of_edges()
    )

    st.divider()

    st.write("### 💡 Example questions")

    st.write(
        "• Tell me about Training to Farmers"
    )

    st.write(
        "• What are the benefits of Training to Farmers?"
    )

    st.write(
        "• Who is eligible for Training to Farmers?"
    )

# ==========================================
# CHAT HISTORY
# ==========================================

if "messages" not in st.session_state:

    st.session_state.messages = []


# Display previous messages

for message in st.session_state.messages:

    with st.chat_message(message["role"]):

        st.markdown(message["content"])


# ==========================================
# CHAT INPUT
# ==========================================

question = st.chat_input(
    "Ask about an agriculture scheme..."
)


if question:

    # User message

    st.session_state.messages.append(
        {
            "role": "user",
            "content": question
        }
    )

    with st.chat_message("user"):

        st.markdown(question)


    # Assistant response

    with st.chat_message("assistant"):

        with st.spinner("Searching the knowledge graph..."):

            try:

                answer = answer_question(question)

                st.markdown(answer)

            except Exception as e:

                answer = (
                    f"⚠️ Something went wrong: {e}"
                )

                st.error(answer)


    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": answer
        }
    )