# src/agentic/core/tutor_escalator.py

def route_tutor_crash_escalation(exception: Exception, param: str, user_input: str, full_verbose_trace: str) -> str:
    """Intercepts tool failures and routes system context to the appropriate fallback agent."""
    error_msg = str(exception)
    
    if isinstance(exception, LookupError) or "missing essential context" in error_msg.lower():
        from document_concept_agent import DocumentConceptAgent
        doc_agent = DocumentConceptAgent()
        agent_proposal = doc_agent.execute_document_recovery_loop(
            failed_task=f"Resolve empty vector-search bounds for parameter: '{param if param else user_input}'",
            error_trace=full_verbose_trace
        )
        return "Document Concept Agent", agent_proposal
    else:
        from codebase_guru.code_refactor_agent import run_agent_loop
        agent_proposal = run_agent_loop(
            user_objective=f"Fix a code exception inside tutor_engine.py. Trace:\n\n{full_verbose_trace}",
            target_area="agentic/tutor_engine.py"
        )
        return "Code Refactor Agent", agent_proposal
