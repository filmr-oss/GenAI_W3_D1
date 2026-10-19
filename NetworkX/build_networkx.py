import os
import pickle

from Neo4j.scraper import fetch_tn_schemes


# ============================================================
# NETWORKX
# ============================================================

import networkx as nx


# ============================================================
# CREATE GRAPH
# ============================================================

graph = nx.DiGraph()

print("========================================")
print("🌾 Building NetworkX Scheme Graph")
print("========================================")


# ============================================================
# SCRAPE DATA
# ============================================================

print("\n📥 Scraping Tamil Nadu Government schemes...")

docs = fetch_tn_schemes(limit=None)

print(f"\n✅ Schemes scraped: {len(docs)}")


# ============================================================
# BUILD GRAPH
# ============================================================

for index, doc in enumerate(docs, start=1):

    scheme = doc.metadata.get("scheme", "").strip()
    source = doc.metadata.get("source", "")

    if not scheme:
        continue

    text = doc.page_content

    # --------------------------------------------------------
    # Extract useful information directly from scraped text
    # --------------------------------------------------------

    def get_value(field, next_field):

        start = text.find(field)

        if start == -1:
            return ""

        start += len(field)

        end = text.find(next_field, start)

        if end == -1:
            value = text[start:]
        else:
            value = text[start:end]

        return " ".join(value.strip().split())


    department = get_value(
        "Concerned Department:",
        "Concerned District:"
    )

    funding = get_value(
        "Funding Pattern:",
        "Beneficiaries:"
    )

    beneficiaries = get_value(
        "Beneficiaries:",
        "Types of Benefits:"
    )

    benefits = get_value(
        "Types of Benefits:",
        "Eligibility criteria:"
    )

    description = get_value(
        "Description:",
        "Scheme Type:"
    )


    # ========================================================
    # SCHEME NODE
    # ========================================================

    graph.add_node(
        scheme,
        type="Scheme",
        description=description,
        funding=funding,
        source=source
    )


    # ========================================================
    # DEPARTMENT
    # ========================================================

    if department and department != "-":

        graph.add_node(
            department,
            type="Department"
        )

        graph.add_edge(
            scheme,
            department,
            relationship="OFFERED_BY"
        )


    # ========================================================
    # BENEFICIARY
    # ========================================================

    if beneficiaries and beneficiaries != "-":

        graph.add_node(
            beneficiaries,
            type="Beneficiary"
        )

        graph.add_edge(
            scheme,
            beneficiaries,
            relationship="APPLIES_TO"
        )


    # ========================================================
    # BENEFIT
    # ========================================================

    if benefits and benefits != "-":

        graph.add_node(
            benefits,
            type="Benefit"
        )

        graph.add_edge(
            scheme,
            benefits,
            relationship="PROVIDES_BENEFIT"
        )


    # ========================================================
    # ELIGIBILITY
    # ========================================================

    if description:

        eligibility_node = f"{scheme}_eligibility"

        graph.add_node(
            eligibility_node,
            type="EligibilityCriteria",
            description=description
        )

        graph.add_edge(
            scheme,
            eligibility_node,
            relationship="HAS_CRITERIA"
        )


    print(f"   ✅ {scheme}")


# ============================================================
# SAVE GRAPH
# ============================================================

os.makedirs("data", exist_ok=True)

graph_path = "data/scheme_graph.pkl"

with open(graph_path, "wb") as file:

    pickle.dump(graph, file)


# ============================================================
# STATISTICS
# ============================================================

print("\n========================================")
print("🎉 NETWORKX GRAPH COMPLETE")
print("========================================")

print(
    f"Nodes: {graph.number_of_nodes()}"
)

print(
    f"Relationships: {graph.number_of_edges()}"
)


print("\n📊 Node types:")

node_types = {}

for node, data in graph.nodes(data=True):

    node_type = data.get("type", "Unknown")

    node_types[node_type] = (
        node_types.get(node_type, 0) + 1
    )


for node_type, count in node_types.items():

    print(
        f"{node_type}: {count}"
    )


print("\n🔗 Relationship types:")

relationship_types = {}

for source, target, data in graph.edges(data=True):

    relationship = data.get(
        "relationship",
        "Unknown"
    )

    relationship_types[relationship] = (
        relationship_types.get(
            relationship,
            0
        ) + 1
    )


for relationship, count in relationship_types.items():

    print(
        f"{relationship}: {count}"
    )


print("\n💾 Graph saved to:")

print(graph_path)

print("\n✅ NetworkX knowledge graph ready!")