import logging
import os

logger = logging.getLogger("ZaraAI_DeployAgent")


async def deploy_fix(patch_data: str, commit_msg: str = "fix(ai): Autonomous bug resolution sequence"):
    """
    Records an AI-generated patch for human review.

    This agent previously ran `git checkout -b / add . / commit` and, on failure,
    `git reset --hard` + `git checkout main` in the server's working directory — which
    could commit unrelated work or destroy uncommitted changes on a developer machine.
    It now never touches git. Patches are only logged; a human applies them.
    """
    if os.getenv("ZARA_AUTO_HEAL_ENABLED", "false").strip().lower() != "true":
        logger.info("Autonomous deploy is disabled (ZARA_AUTO_HEAL_ENABLED is not 'true'). Patch not applied.")
        return

    preview = (patch_data or "")[:2000]
    logger.warning(
        "Autonomous patch generated and held for HUMAN REVIEW (not applied, not committed).\n"
        f"Suggested commit message: {commit_msg}\n--- patch preview ---\n{preview}"
    )
