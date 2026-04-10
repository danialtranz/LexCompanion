from .state import AgentState


def generate_response(state: AgentState) -> AgentState:
    text = state["user_input"].strip()
    return {
        "user_input": text,
        "response": f"LangGraph base says: {text}",
    }
