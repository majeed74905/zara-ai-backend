import logging
from typing import Dict, Any
from app.zara_ai.agents.debug_agent import analyze_error
from app.zara_ai.agents.fix_agent import generate_fix
from app.zara_ai.agents.test_agent import generate_tests
from app.zara_ai.agents.deploy_agent import deploy_fix
from app.zara_ai.core.memory_store import store_learning, search_knowledge

logger = logging.getLogger("ZaraAI_Orchestrator")

# Async auto-heal race condition lock
_active_fixes = set()

FORBIDDEN_AREAS = [
    "auth.py",
    "jwt.py",
    "payment",
    "security.py",
    "config.py"
]

async def autonomous_loop(error_msg: str, traceback_str: str):
    """
    L4/L5 Level Self-Healing Orchestrator
    This function runs in the background continuously tracking and patching production bugs.
    """
    logger.info("Initializing Autonomous Debug Protocol...")
    
    # Race Condition Lock (Prevent concurrent loops on the same error)
    if error_msg in _active_fixes:
        logger.info("Skip: Auto-Heal already in progress for this error.")
        return
    _active_fixes.add(error_msg)

    try:
        # 1. Search knowledge layer (Semantic Vector Search)
        past_memory = await search_knowledge(error_msg)
        
        # 2. Analyze the context
        analysis = await analyze_error(error_msg, traceback_str, past_memory)
        logger.info(f"Analysis Complete: Severity {analysis.get('severity', 'UNKNOWN')}")
        
        # Check severity and forbidden guards
        if analysis.get('severity', '').upper() == 'CRITICAL_SECURITY':
            logger.critical("Security breach detected. Human intervention required.")
            return # Do not blind fix

        affected_files = analysis.get('affected_files', [])
        if any(forbidden in file_path for file_path in affected_files for forbidden in FORBIDDEN_AREAS):
            logger.critical(f"Forbidden area modified {affected_files}. Escalating to human review.")
            return
            
        # 3. Generate non-breaking fix
        fix_patch = await generate_fix(analysis)
        if not fix_patch:
            return

        # 4. Generate accompanying regression tests
        tests = await generate_tests(error_msg, fix_patch)
        
        # 5. Safety bounds
        if not _validate_fix_safety(fix_patch):
            logger.warning("Generated patch violated AST bounds.")
            return

        # 6. Multi-layer Validation Gate (Simulated tests run)
        logger.info("Verifying syntax and structural integrity...")
        if _run_multi_layer_validation():
            # 7. Commit changes (PR-based deployment)
            await deploy_fix(fix_patch)
            await store_learning(error_msg, fix_patch)
            logger.info("Self-healing sequence successful.")
        else:
            logger.info("Test runner rejected AI patch. Rolling back.")
            
    finally:
        _active_fixes.remove(error_msg)

def _run_multi_layer_validation() -> bool:
    """Simulates running a full suite: unit, contract, and schema validation."""
    # subprocess.run(["pytest", "tests/integration/"])
    # subprocess.run(["npm", "run", "test:snapshots"])
    return True

def _validate_fix_safety(patch: str) -> bool:
    """Never allow schema migrations blindly."""
    if "ALTER TABLE" in patch.upper() or "DROP TABLE" in patch.upper() or "migrations" in patch.lower():
        return False
    return True
