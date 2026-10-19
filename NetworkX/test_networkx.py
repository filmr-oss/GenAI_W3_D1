import pickle

with open("../data/scheme_graph.pkl", "rb") as file:
    graph = pickle.load(file)

print("========================================")
print("🌾 NetworkX Graph Test")
print("========================================")

print(f"Nodes: {graph.number_of_nodes()}")
print(f"Relationships: {graph.number_of_edges()}")

scheme = "Training to Farmers"

if scheme in graph:
    print(f"\n✅ Found scheme: {scheme}")

    print("\n🔗 Relationships:")

    for target in graph.successors(scheme):
        relationship = graph[scheme][target]["relationship"]
        print(f"  {relationship} → {target}")

else:
    print(f"\n❌ Scheme not found: {scheme}")