from app.zara_ai.core.memory_store import store_learning, search_knowledge

# Learning Agent wrapper. In L5 autonomy, this would also 
# analyze trends across past patches to refactor the architecture.

def learn_from_fix(error_trace: str, successful_patch: str, success_metrics: dict):
    """
    Stores heuristics of the fix.
    """
    pattern_type = "functional"
    if "jwt" in error_trace.lower() or "auth" in error_trace.lower():
        pattern_type = "authentication_circuit"
        
    store_learning(error_trace, successful_patch, pattern=pattern_type)
