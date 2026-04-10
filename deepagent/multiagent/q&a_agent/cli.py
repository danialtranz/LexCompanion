from dotenv import load_dotenv

from .agent import graph


def main() -> None:
    load_dotenv()
    result = graph.invoke({"user_input": "Hello LangGraph", "response": ""})
    print(result["response"])


if __name__ == "__main__":
    main()
