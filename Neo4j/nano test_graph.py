import os
from dotenv import load_dotenv
from langchain_neo4j import Neo4jGraph

load_dotenv()

graph = Neo4jGraph(
    url=os.getenv("NEO4J_URI"),
    username=os.getenv("NEO4J_USERNAME"),
    password=os.getenv("NEO4J_PASSWORD"),
    database=os.getenv("NEO4J_DATABASE"),
)

result = graph.query("""
MATCH (s:Scheme)
WHERE toLower(s.id) = toLower('Training to Farmers')
RETURN s.id, s.description
""")

print(result)