import os
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_neo4j import Neo4jGraph
from langchain_neo4j.chains.graph_qa.cypher import GraphCypherQAChain
from langchain_core.prompts import PromptTemplate


# ============================================
# Load environment variables
# ============================================

load_dotenv()


# ============================================
# Neo4j Connection
# ============================================

print("================================")
print("🌾 Tamil Nadu Scheme AI")
print("================================")

print("\nConnecting to Neo4j...")

graph = Neo4jGraph(
    url=os.getenv("NEO4J_URI"),
    username=os.getenv("NEO4J_USERNAME"),
    password=os.getenv("NEO4J_PASSWORD"),
    database=os.getenv("NEO4J_DATABASE"),
)

print("✅ Connected to Neo4j")


# ============================================
# OpenAI LLM
# ============================================

llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0
)


# ============================================
# Custom Cypher Prompt
# ============================================

cypher_prompt = PromptTemplate.from_template("""
You are an expert Neo4j Cypher query generator.

Your job is to convert the user's question into a valid Cypher query.

Use ONLY the graph schema provided below.

GRAPH SCHEMA:

{schema}

IMPORTANT RULES:

1. Scheme nodes use the label `Scheme`.

2. Scheme names are stored in the `id` property.

3. Scheme names may have different capitalization.

4. Always use case-insensitive matching when searching for a scheme name.

Example:

MATCH (s:Scheme)
WHERE toLower(s.id) = toLower('Training to Farmers')
RETURN s

5. If the user asks about a specific scheme, search the Scheme node.

6. If the user asks who provides a scheme, use the OFFERED_BY relationship.

7. If the user asks who is eligible, asks about eligibility, eligible farmers,
   beneficiaries, or who can apply:

   ALWAYS return the Scheme description.

   DO NOT use the APPLIES_TO relationship for these questions.

Example:

MATCH (s:Scheme)
WHERE toLower(s.id) = toLower('Training to Farmers')
RETURN s.description

8. If the user asks about benefits, use the PROVIDES_BENEFIT relationship.

9. If the user asks about criteria, use the HAS_CRITERIA relationship.

10. If the user asks about required documents, use the REQUIRES_DOCUMENT relationship.

11. If the user asks for a general description of a scheme, return the Scheme node.

12. Do not invent labels, properties, or relationships.

13. Return ONLY the Cypher query.

USER QUESTION:

{question}

CYPHER QUERY:
""")


# ============================================
# Graph Question Answering Chain
# ============================================

chain = GraphCypherQAChain.from_llm(
    llm=llm,
    graph=graph,
    verbose=True,
    allow_dangerous_requests=True,
    validate_cypher=True,
    cypher_prompt=cypher_prompt
)


# ============================================
# Interactive Question Loop
# ============================================

print("\n--------------------------------")
print("🌾 Tamil Nadu Agriculture Scheme AI")
print("--------------------------------")
print("Ask questions about Tamil Nadu")
print("Agriculture & Farmers Welfare schemes.")
print("\nType 'exit' to quit.\n")


while True:

    question = input("You: ")

    # Exit
    if question.lower().strip() == "exit":
        print("\nGoodbye! 👋")
        break

    # Ignore empty questions
    if not question.strip():
        continue

    try:

        response = chain.invoke({
            "query": question
        })

        print("\n🤖 AI:")
        print(response["result"])
        print()

    except Exception as e:

        print("\n❌ Error:")
        print(e)
        print()