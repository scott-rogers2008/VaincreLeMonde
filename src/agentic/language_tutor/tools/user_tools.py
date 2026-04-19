# tools/user_tools.py

from smolagents import tool

@tool
def ask_user_confirmation(question: str) -> str:
    """
    Displays a question to the user and returns their response (yes/no/feedback).
    Use this for summary approvals.
    Args:
        question: The qeustion that will be asked of the user.
    """
    print(f"\n[AGENT QUERY]: {question}")
    return input("User Response > ")
