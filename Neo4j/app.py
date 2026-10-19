import os
import re

import streamlit as st
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_neo4j import Neo4jGraph
from langchain_neo4j.chains.graph_qa.cypher import GraphCypherQAChain
from langchain_core.prompts import PromptTemplate


# ============================================================
# LOAD ENVIRONMENT
# ============================================================

load_dotenv()


# ============================================================
# STREAMLIT CONFIG
# ============================================================

st.set_page_config(
    page_title="Tamil Nadu Scheme AI",
    page_icon="🌾",
    layout="centered"
)


# ============================================================
# HEADER
# ============================================================

st.title("🌾 Tamil Nadu Scheme AI")

st.caption(
    "Ask questions about Tamil Nadu Government "
    "Agriculture & Farmers Welfare schemes."
)

st.divider()


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.header("🌾 About")

    st.write(
        "Tamil Nadu Scheme AI helps users find information "
        "about Government Agriculture & Farmers Welfare schemes "
        "using a Neo4j knowledge graph."
    )

    st.divider()

    st.subheader("💡 Example Questions")

    st.write("• Tell me about Training to Farmers")
    st.write("• Who is eligible?")
    st.write("• What are the benefits?")
    st.write("• Who provides the scheme?")
    st.write("• Who can apply?")
    st.write("• What are the eligibility criteria?")

    st.divider()

    st.caption("Powered by OpenAI + Neo4j")


# ============================================================
# CREATE AI CONNECTIONS
# ============================================================

@st.cache_resource
def create_ai():

    graph = Neo4jGraph(
        url=os.getenv("NEO4J_URI"),
        username=os.getenv("NEO4J_USERNAME"),
        password=os.getenv("NEO4J_PASSWORD"),
        database=os.getenv("NEO4J_DATABASE"),
    )

    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0
    )

    cypher_prompt = PromptTemplate.from_template(
        """
You are an expert Neo4j Cypher query generator.

Convert the user's question into a valid Cypher query.

Use ONLY the graph schema provided below.

GRAPH SCHEMA:

{schema}

GRAPH STRUCTURE:

(:Scheme)

Properties:

- id
- description
- funding
- scheme_type
- source

Relationships:

(:Scheme)-[:OFFERED_BY]->(:Department)

(:Scheme)-[:APPLIES_TO]->(:Beneficiary)

(:Scheme)-[:PROVIDES_BENEFIT]->(:Benefit)

(:Scheme)-[:HAS_CRITERIA]->(:EligibilityCriteria)

(:Scheme)-[:HAS_APPLICATION_PROCESS]->(:ApplicationProcess)

RULES:

1. Scheme names are stored in the `id` property.

2. Always use case-insensitive scheme matching.

3. Use only labels, properties and relationships that exist
   in the graph schema.

4. Do not invent information.

5. Return ONLY valid Cypher.

6. Do not return explanations.

USER QUESTION:

{question}

CYPHER QUERY:
"""
    )

    chain = GraphCypherQAChain.from_llm(
        llm=llm,
        graph=graph,
        verbose=True,
        allow_dangerous_requests=True,
        validate_cypher=True,
        cypher_prompt=cypher_prompt
    )

    return graph, llm, chain


# ============================================================
# CONNECT
# ============================================================

try:

    graph, llm, chain = create_ai()

except Exception as e:

    st.error("❌ Unable to connect to Neo4j.")

    st.code(str(e))

    st.stop()


# ============================================================
# SESSION STATE
# ============================================================

if "messages" not in st.session_state:
    st.session_state.messages = []


if "current_scheme" not in st.session_state:
    st.session_state.current_scheme = None


# ============================================================
# DISPLAY CHAT HISTORY
# ============================================================

for message in st.session_state.messages:

    with st.chat_message(message["role"]):

        st.markdown(message["content"])


# ============================================================
# CHAT INPUT
# ============================================================

question = st.chat_input(
    "Ask about a Tamil Nadu government scheme..."
)


# ============================================================
# PROCESS QUESTION
# ============================================================

if question:

    # --------------------------------------------------------
    # SAVE USER MESSAGE
    # --------------------------------------------------------

    st.session_state.messages.append(
        {
            "role": "user",
            "content": question
        }
    )

    with st.chat_message("user"):
        st.markdown(question)


    # --------------------------------------------------------
    # PREVIOUS CONVERSATION
    # --------------------------------------------------------

    previous_messages = st.session_state.messages[:-1]

    conversation_text = ""

    for message in previous_messages[-8:]:

        conversation_text += (
            f"{message['role'].upper()}: "
            f"{message['content']}\n"
        )


    # --------------------------------------------------------
    # ANSWER
    # --------------------------------------------------------

    with st.chat_message("assistant"):

        with st.spinner("🔎 Searching scheme database..."):

            try:

                # ====================================================
                # STEP 1 — REWRITE FOLLOW-UP QUESTION
                # ====================================================

                rewrite_prompt = f"""
You are helping a Tamil Nadu government scheme chatbot.

Rewrite the latest user question into a standalone question.

Use the conversation history to identify the scheme.

If the latest question is a follow-up such as:

- Who is eligible?
- What are the benefits?
- Who provides it?
- Who can apply?
- What are the criteria?

identify the scheme from the previous conversation.

Do NOT answer the question.

Return ONLY the rewritten question.

CONVERSATION:

{conversation_text}

LATEST QUESTION:

{question}
"""

                rewritten_question = llm.invoke(
                    rewrite_prompt
                ).content.strip()

                print(
                    "\n🔄 Rewritten question:",
                    rewritten_question
                )


                # ====================================================
                # STEP 2 — FIND SCHEME FROM DATABASE
                # ====================================================

                # First try to identify a scheme explicitly
                # mentioned in the rewritten question.

                all_schemes = graph.query(
                    """
                    MATCH (s:Scheme)
                    RETURN s.id AS scheme
                    ORDER BY s.id
                    """
                )


                scheme_names = [
                    row["scheme"]
                    for row in all_schemes
                    if row.get("scheme")
                ]


                detected_scheme = None


                # ----------------------------------------------------
                # Match scheme name against question
                # ----------------------------------------------------

                question_lower = rewritten_question.lower()

                # Prefer longest names first.
                # This avoids matching a short name inside a longer one.

                for scheme in sorted(
                    scheme_names,
                    key=len,
                    reverse=True
                ):

                    if scheme.lower() in question_lower:

                        detected_scheme = scheme

                        break


                # ----------------------------------------------------
                # If no scheme found, use previous scheme
                # ----------------------------------------------------

                if not detected_scheme:

                    detected_scheme = (
                        st.session_state.current_scheme
                    )


                # ----------------------------------------------------
                # Save current scheme
                # ----------------------------------------------------

                if detected_scheme:

                    st.session_state.current_scheme = (
                        detected_scheme
                    )


                print(
                    "🌾 Current scheme:",
                    st.session_state.current_scheme
                )


                # ====================================================
                # STEP 3 — QUESTION TYPE
                # ====================================================

                lower_question = rewritten_question.lower()


                benefit_keywords = [
                    "benefit",
                    "benefits",
                    "subsidy",
                    "financial assistance",
                    "assistance",
                    "what does the scheme provide"
                ]


                eligibility_keywords = [
                    "eligible",
                    "eligibility",
                    "who can apply",
                    "who is eligible",
                    "eligibility criteria",
                    "criteria"
                ]


                beneficiary_keywords = [
                    "beneficiary",
                    "beneficiaries",
                    "who can get",
                    "who can receive",
                    "who is this for"
                ]


                provider_keywords = [
                    "who provides",
                    "provider",
                    "department",
                    "which department",
                    "offered by"
                ]


                is_benefit_question = any(
                    keyword in lower_question
                    for keyword in benefit_keywords
                )


                is_eligibility_question = any(
                    keyword in lower_question
                    for keyword in eligibility_keywords
                )


                is_beneficiary_question = any(
                    keyword in lower_question
                    for keyword in beneficiary_keywords
                )


                is_provider_question = any(
                    keyword in lower_question
                    for keyword in provider_keywords
                )


                # ====================================================
                # STEP 4 — STRUCTURED NEO4J QUESTIONS
                # ====================================================

                if (
                    detected_scheme
                    and (
                        is_benefit_question
                        or is_eligibility_question
                        or is_beneficiary_question
                        or is_provider_question
                    )
                ):

                    # =================================================
                    # BENEFITS
                    # =================================================

                    if is_benefit_question:

                        result = graph.query(
                            """
                            MATCH (s:Scheme)
                            WHERE toLower(s.id) = toLower($scheme)

                            OPTIONAL MATCH
                                (s)-[:PROVIDES_BENEFIT]->(b:Benefit)

                            RETURN
                                s.id AS scheme,
                                collect(b.id) AS benefits
                            """,

                            params={
                                "scheme": detected_scheme
                            }
                        )


                        if result and result[0]["scheme"]:

                            benefits = [
                                x
                                for x in result[0]["benefits"]
                                if x
                            ]


                            if benefits:

                                answer = (
                                    f"**{result[0]['scheme']}** "
                                    f"provides:\n\n"
                                    + "\n".join(
                                        f"• {benefit}"
                                        for benefit in benefits
                                    )
                                )

                            else:

                                answer = (
                                    "No specific benefit information "
                                    "was found for this scheme."
                                )

                        else:

                            answer = (
                                "I couldn't find this scheme "
                                "in the database."
                            )


                    # =================================================
                    # ELIGIBILITY
                    # =================================================

                    elif is_eligibility_question:

                        result = graph.query(
                            """
                            MATCH (s:Scheme)
                            WHERE toLower(s.id) = toLower($scheme)

                            OPTIONAL MATCH
                                (s)-[:HAS_CRITERIA]->(e:EligibilityCriteria)

                            RETURN
                                s.id AS scheme,
                                collect(e.id) AS criteria
                            """,

                            params={
                                "scheme": detected_scheme
                            }
                        )


                        if result and result[0]["scheme"]:

                            criteria = [
                                x
                                for x in result[0]["criteria"]
                                if x
                            ]


                            if criteria:

                                answer = (
                                    f"**Eligibility for "
                                    f"{result[0]['scheme']}:**\n\n"
                                    + "\n".join(
                                        f"• {criterion}"
                                        for criterion in criteria
                                    )
                                )

                            else:

                                answer = (
                                    "Eligibility information is "
                                    "not available for this scheme."
                                )

                        else:

                            answer = (
                                "I couldn't find this scheme "
                                "in the database."
                            )


                    # =================================================
                    # BENEFICIARY
                    # =================================================

                    elif is_beneficiary_question:

                        result = graph.query(
                            """
                            MATCH (s:Scheme)
                            WHERE toLower(s.id) = toLower($scheme)

                            OPTIONAL MATCH
                                (s)-[:APPLIES_TO]->(b:Beneficiary)

                            RETURN
                                s.id AS scheme,
                                collect(b.id) AS beneficiaries
                            """,

                            params={
                                "scheme": detected_scheme
                            }
                        )


                        if result and result[0]["scheme"]:

                            beneficiaries = [
                                x
                                for x in result[0]["beneficiaries"]
                                if x
                            ]


                            if beneficiaries:

                                answer = (
                                    f"**Beneficiaries of "
                                    f"{result[0]['scheme']}:**\n\n"
                                    + "\n".join(
                                        f"• {beneficiary}"
                                        for beneficiary in beneficiaries
                                    )
                                )

                            else:

                                answer = (
                                    "Beneficiary information is "
                                    "not available."
                                )

                        else:

                            answer = (
                                "I couldn't find this scheme "
                                "in the database."
                            )


                    # =================================================
                    # PROVIDER
                    # =================================================

                    else:

                        result = graph.query(
                            """
                            MATCH (s:Scheme)
                            WHERE toLower(s.id) = toLower($scheme)

                            OPTIONAL MATCH
                                (s)-[:OFFERED_BY]->(d:Department)

                            RETURN
                                s.id AS scheme,
                                collect(d.id) AS departments
                            """,

                            params={
                                "scheme": detected_scheme
                            }
                        )


                        if result and result[0]["scheme"]:

                            departments = [
                                x
                                for x in result[0]["departments"]
                                if x
                            ]


                            if departments:

                                answer = (
                                    f"**{result[0]['scheme']}** "
                                    f"is offered by:\n\n"
                                    + "\n".join(
                                        f"• {department}"
                                        for department in departments
                                    )
                                )

                            else:

                                answer = (
                                    "Department information is "
                                    "not available."
                                )

                        else:

                            answer = (
                                "I couldn't find this scheme "
                                "in the database."
                            )


                # ====================================================
                # STEP 5 — GENERAL QUESTION
                # ====================================================

                else:

                    response = chain.invoke(
                        {
                            "query": rewritten_question
                        }
                    )

                    answer = response["result"]


                # ====================================================
                # DISPLAY
                # ====================================================

                st.markdown(answer)


            except Exception as e:

                answer = (
                    "Sorry, I couldn't process your question.\n\n"
                    f"Error: {e}"
                )

                st.error(answer)


    # ========================================================
    # SAVE ASSISTANT RESPONSE
    # ========================================================

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": answer
        }
    )