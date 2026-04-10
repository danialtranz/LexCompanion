from langgraph.graph import END, START, StateGraph

from .nodes import generate_response
from .state import AgentState


builder = StateGraph(AgentState)
builder.add_node("generate_response", generate_response)
builder.add_edge(START, "generate_response")
builder.add_edge("generate_response", END)

graph = builder.compile()
