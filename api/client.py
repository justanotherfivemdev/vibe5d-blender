from typing import Dict, Any, Tuple

from ..utils.logger import logger


class APIClient:
    """Stub cloud API client retained for import compatibility.

    Vibe5D is fully local/direct-provider-first.  The hosted cloud
    API has been removed.  All methods return failure so legacy code
    paths fail gracefully.
    """

    def __init__(self):
        self.timeout = 30

    def verify_license(self, license_key: str) -> Tuple[bool, Dict[str, Any]]:
        logger.debug("verify_license called (hosted API removed)")
        return False, {"error": "Hosted API has been removed. Use a direct LLM provider instead."}

    def validate_user_token(self, user_id: str, token: str) -> Tuple[bool, str]:
        logger.debug("validate_user_token called (hosted API removed)")
        return False, "auth"

    def get_usage_info(self, user_id: str, token: str) -> Tuple[bool, Dict[str, Any]]:
        logger.debug("get_usage_info called (hosted API removed)")
        return False, {"error": "Hosted API has been removed."}

    def upload_image(self, chat_id: str, image_data: bytes, source_type: str, user_id: str, token: str) -> Tuple[
        bool, str]:
        logger.debug("upload_image called (hosted API removed)")
        return False, ""

    def download_image(self, chat_id: str, image_id: str, user_id: str, token: str) -> Tuple[bool, bytes]:
        logger.debug("download_image called (hosted API removed)")
        return False, b""


api_client = APIClient()
