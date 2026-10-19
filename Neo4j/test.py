import os

from dotenv import load_dotenv
from langchain_neo4j import Neo4jGraph


load_dotenv()


print("================================")
print("Neo4j Connection Test")
print("================================")


uri = os.getenv("NEO4J_URI")
username = os.getenv("NEO4J_USERNAME")
password = os.getenv("NEO4J_PASSWORD")
database = os.getenv(
    "NEO4J_DATABASE",
    "neo4j"
)


print(f"URI: {uri}")
print(f"Username: {username}")
print(
    f"Password configured: {bool(password)}"
)
print(f"Database: {database}")


if not uri:
    raise ValueError(
        "NEO4J_URI is missing from .env"
    )

if not username:
    raise ValueError(
        "NEO4J_USERNAME is missing from .env"
    )

if not password:
    raise ValueError(
        "NEO4J_PASSWORD is missing from .env"
    )


print("\nConnecting...")


try:

    graph = Neo4jGraph(
        url=uri,
        username=username,
        password=password,
        database=database
    )

    print("✓ Connected to Neo4j!")

    result = graph.query(
        "RETURN 'Hello Neo4j' AS message"
    )

    print("\nTest query result:")

    print(result)

    print(
        "\n✓ Neo4j is working correctly."
    )

except Exception as e:

    print("\n❌ Neo4j connection failed.")

    print(type(e).__name__)
    print(e)