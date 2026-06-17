# src/agentic/language_tutor/tools/user_tools.py

def ask_user_confirmation(question: str) -> str:
    """Displays an engineering confirmation message to the interactive terminal window."""
    print(f"\n[AGENT QUERY]: {question}")
    return input("User Response > ")
