from ..utils.logger import logger


class AuthManager:
    """Stub auth manager retained for API compatibility.

    Vibe5D is fully local/direct-provider-first.  Hosted cloud
    authentication has been removed.  All methods are no-ops that
    preserve the call-site contract so existing callers don't crash.
    """

    def __init__(self):
        self.is_initialized = False

    def initialize_auth(self, context) -> bool:
        self.is_initialized = True
        return True

    def save_auth_state(self, context) -> bool:
        return True

    def clear_auth_state(self, context) -> bool:
        self.is_initialized = False
        logger.debug("Auth state cleared (no-op)")
        return True

    def reset_auth_manager(self):
        self.is_initialized = False
        logger.debug("Auth manager reset (no-op)")

    def is_authenticated(self, context) -> bool:
        return False

    def get_user_info(self, context):
        return None

    def get_auth_headers(self, context):
        return None

    def logout(self, context):
        logger.debug("Logout called (no-op)")

    def reset_user_state(self, context):
        try:
            context.scene.vibe5d_is_generating = False
            context.scene.vibe5d_generation_progress = 0
            context.scene.vibe5d_generation_stage = ""
            context.scene.vibe5d_output_content = ""
            context.scene.vibe5d_final_code = ""
            context.scene.vibe5d_guide_content = ""
            context.scene.vibe5d_last_error = ""
        except Exception:
            pass

    def update_usage_info(self, context) -> bool:
        return False


auth_manager = AuthManager()
