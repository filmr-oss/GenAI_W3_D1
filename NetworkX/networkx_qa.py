import os
import pickle

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# Load saved NetworkX graph
with open("../data/scheme_graph.pkl", "rb") as file:
    graph = pickle.load(file)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def find_scheme(question):
    """
    Find the scheme name mentioned in the user's question.
    Uses the longest matching scheme name.
    """

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
    """
    Extract information about a scheme from NetworkX.
    """

    data = graph.nodes[scheme]

    result = {
        "scheme": scheme,
        "description": data.get("description", ""),
        "funding": data.get("funding", ""),
        "source": data.get("source", ""),
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
                "description", ""
            )

    return result


def answer_question(question):
    """
    Find the relevant scheme in NetworkX
    and generate an answer using OpenAI.
    """

    scheme = find_scheme(question)

    if not scheme:
        return (
            "I couldn't identify a Tamil Nadu government scheme "
            "in your question. Please mention the scheme name."
        )

    scheme_data = get_scheme_data(scheme)

    context = f"""
Scheme Name: {scheme_data.get("scheme", "")}

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
You are a helpful assistant for Tamil Nadu Government Agriculture schemes.

Answer the user's question using ONLY the information provided
in the NetworkX knowledge graph context.

Do not invent information.

If the information is not available, clearly say that it is
not available in the knowledge graph.

Keep the answer simple and clear.

Knowledge Graph Context:
{context}

User Question:
{question}
"""

    response = client.responses.create(
        model="gpt-6-luna",
        input=prompt
    )

    return response.output_text


if __name__ == "__main__":

    print("========================================")
    print("🌾 NetworkX + OpenAI QA Test")
    print("========================================")

    question = input("\nAsk a question: ")

    answer = answer_question(question)

    print("\n🤖 Answer:")
    print(answer)