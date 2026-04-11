from dotenv import load_dotenv

#try:
from agent import build_graph
# except ImportError:
#     import pathlib
#     import sys

#     current_dir = pathlib.Path(__file__).resolve().parent
#     parent_dir = current_dir.parent
#     if str(parent_dir) not in sys.path:
#         sys.path.insert(0, str(parent_dir))
#     from importlib import import_module

#     graph = import_module("q2a_agent.agent").graph


def main() -> None:
    load_dotenv()
    graph = build_graph()
    result = graph.invoke({"user_input": "Hello LangGraph", "response": ""})
    print(result["response"])


if __name__ == "__main__":
    main()
