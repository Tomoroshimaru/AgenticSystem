from main import build_graph

builder = build_graph()
graph = builder.compile()

# Print Mermaid diagram
print(graph.get_graph().draw_mermaid())