import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Dict, Any, Tuple

from ..utils.json_utils import BlenderJSONEncoder
from ..utils.logger import logger


class APIClient:
    BASE_URL = "https://api.vibe5d.local"

    ERROR_CODES = {
        0: "CLIENT_ERROR",
        6: "MAINTENANCE_MODE",
        101: "INVALID_REQUEST",
        102: "INTERNAL_SERVER_ERROR",
        103: "AUTHORIZATION_FAILED",
        106: "NOT_FOUND",
        109: "TOO_MANY_REQUESTS",
        110: "ALREADY_EXISTS",
        111: "YOU_ARE_BEING_RATE_LIMITED",
        112: "OUTDATED_CLIENT",
        1404: "WRONG_PATH"
    }

    def __init__(self):
        self.timeout = 60

    def _make_request(self, endpoint: str, data: Dict[str, Any] = None, method: str = "POST") -> Tuple[
        bool, Dict[str, Any]]:

        url = f"{self.BASE_URL}{endpoint}"

        try:

            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'Vibe5D-Blender-Addon/0.0.4'
            }


            if data:
                json_data = json.dumps(data, cls=BlenderJSONEncoder).encode('utf-8')
            else:
                json_data = None

            req = urllib.request.Request(url, data=json_data, headers=headers, method=method)

            logger.debug(f"Making {method} request to {url}")

            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                response_data = response.read().decode('utf-8')
                result = json.loads(response_data)

                logger.debug(f"API response: {result}")
                return True, result

        except urllib.error.HTTPError as e:
            logger.error(f"HTTP error {e.code}: {e.reason}")
            try:
                error_data = json.loads(e.read().decode('utf-8'))
                return False, error_data
            except:
                return False, {"error": f"HTTP {e.code}: {e.reason}"}

        except urllib.error.URLError as e:
            logger.error(f"URL error: {e.reason}")
            return False, {"error": f"Connection error: {e.reason}"}

        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            return False, {"error": "Invalid JSON response"}

        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return False, {"error": f"Unexpected error: {str(e)}"}

    def _make_get_request(self, endpoint: str, params: Dict[str, str] = None) -> Tuple[bool, Dict[str, Any]]:

        url = f"{self.BASE_URL}{endpoint}"

        if params:
            query_string = urllib.parse.urlencode(params)
            url = f"{url}?{query_string}"

        try:

            headers = {
                'User-Agent': 'Vibe5D-Blender-Addon/0.0.4'
            }


            req = urllib.request.Request(url, headers=headers, method="GET")

            logger.debug(f"Making GET request to {url}")

            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                response_data = response.read().decode('utf-8')
                result = json.loads(response_data)

                logger.debug(f"API response: {result}")
                return True, result

        except urllib.error.HTTPError as e:
            logger.error(f"HTTP error {e.code}: {e.reason}")
            try:
                error_data = json.loads(e.read().decode('utf-8'))
                return False, error_data
            except:
                return False, {"error": f"HTTP {e.code}: {e.reason}"}

        except urllib.error.URLError as e:
            logger.error(f"URL error: {e.reason}")
            return False, {"error": f"Connection error: {e.reason}"}

        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            return False, {"error": "Invalid JSON response"}

        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return False, {"error": f"Unexpected error: {str(e)}"}

    def verify_license(self, license_key: str) -> Tuple[bool, Dict[str, Any]]:

        logger.info("Verifying license key")

        if not license_key.strip():
            return False, {"error": "License key cannot be empty"}

        data = {"license_key": license_key.strip()}
        success, response = self._make_request("/v1/license/verify", data)

        if not success:
            return False, response

        result = response.get("result", {})
        if result.get("type") != 2 or result.get("code") != 0:
            error_code = result.get("code", 0)
            error_name = self.ERROR_CODES.get(error_code, "UNKNOWN_ERROR")
            error_msg = result.get("message", "Unknown error")

            logger.error(f"API error {error_code} ({error_name}): {error_msg}")
            return False, {"error": f"{error_name}: {error_msg}"}

        data = response.get("data", {})
        if not data.get("valid", False):
            error_msg = data.get("error_message", "License verification failed")
            logger.warning(f"License invalid: {error_msg}")
            return False, {"error": error_msg}

        logger.info("License verified successfully")
        return True, data

    def validate_user_token(self, user_id: str, token: str) -> Tuple[bool, str]:
        if not user_id.strip() or not token.strip():
            logger.warning("Missing user_id or token for validation")
            return False, "auth"

        params = {
            'user_id': user_id.strip(),
            'token': token.strip()
        }

        success, response = self._make_get_request("/api/validateUserToken", params)

        if not success:
            error_msg = response.get('error', 'Unknown error')
            logger.warning(f"Token validation request failed (network error): {error_msg}")
            return False, "network"

        result = response.get("result", {})
        if result.get("type") == 2 and result.get("code") == 0:
            return True, ""
        else:

            if (result.get("type") == 0 and
                    result.get("code") == 6 and
                    result.get("message") == "maintenance"):
                logger.warning("API is in maintenance mode - keeping saved credentials")
                return False, "network"

            error_code = result.get("code", 0)
            error_name = self.ERROR_CODES.get(error_code, "UNKNOWN_ERROR")
            error_msg = result.get("message", "Token validation failed")

            logger.warning(f"Token validation failed - {error_code} ({error_name}): {error_msg}")
            return False, "auth"

    def get_usage_info(self, user_id: str, token: str) -> Tuple[bool, Dict[str, Any]]:
        if not user_id.strip() or not token.strip():
            logger.warning("Missing user_id or token for usage request")
            return False, {"error": "Missing authentication credentials"}

        params = {
            'user_id': user_id.strip(),
            'token': token.strip()
        }

        success, response = self._make_get_request("/v1/usage", params)

        if not success:
            error_msg = response.get('error', 'Unknown error')
            logger.warning(f"Usage request failed (network error): {error_msg}")
            return False, response

        result = response.get("result", {})
        if result.get("type") == 2 and result.get("code") == 0:

            usage_data = response.get("data", {})
            return True, usage_data
        else:

            error_code = result.get("code", 0)
            error_name = self.ERROR_CODES.get(error_code, "UNKNOWN_ERROR")
            error_msg = result.get("message", "Usage request failed")

            logger.warning(f"Usage request failed - {error_code} ({error_name}): {error_msg}")
            return False, {"error": f"{error_name}: {error_msg}"}

    def upload_image(self, chat_id: str, image_data: bytes, source_type: str, user_id: str, token: str) -> Tuple[
        bool, str]:

        if not chat_id or not image_data or not user_id or not token:
            logger.warning("Missing parameters for image upload")
            return False, ""

        try:
            params = {
                'user_id': user_id.strip(),
                'token': token.strip()
            }

            query_string = urllib.parse.urlencode(params)
            url = f"{self.BASE_URL}/api/images/{chat_id}/upload?{query_string}"

            headers = {
                'Content-Type': 'image/png',
                'X-Source-Type': source_type,
                'User-Agent': 'Vibe5D-Blender-Addon/0.0.4'
            }

            req = urllib.request.Request(url, data=image_data, headers=headers, method="POST")

            logger.debug(f"Uploading image to chat {chat_id}, source: {source_type}, size: {len(image_data)} bytes")

            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                response_data = response.read().decode('utf-8')
                result = json.loads(response_data)

                if result.get('result', {}).get('type') == 2 and result.get('result', {}).get('code') == 0:
                    image_id = result.get('data', {}).get('image_id', '')
                    logger.debug(f"Successfully uploaded image: {image_id}")
                    return True, image_id
                else:
                    error_msg = result.get('result', {}).get('message', 'Unknown error')
                    logger.error(f"Failed to upload image: {error_msg}")
                    return False, ""

        except urllib.error.HTTPError as e:
            logger.error(f"HTTP error uploading image {e.code}: {e.reason}")
            return False, ""

        except urllib.error.URLError as e:
            logger.error(f"URL error uploading image: {e.reason}")
            return False, ""

        except Exception as e:
            logger.error(f"Unexpected error uploading image: {str(e)}")
            return False, ""

    def download_image(self, chat_id: str, image_id: str, user_id: str, token: str) -> Tuple[bool, bytes]:

        if not chat_id or not image_id or not user_id or not token:
            logger.warning("Missing parameters for image download")
            return False, b""

        params = {
            'user_id': user_id.strip(),
            'token': token.strip()
        }

        query_string = urllib.parse.urlencode(params)
        url = f"{self.BASE_URL}/api/images/{chat_id}/{image_id}?{query_string}"

        try:
            headers = {
                'User-Agent': 'Vibe5D-Blender-Addon/0.0.4'
            }

            req = urllib.request.Request(url, headers=headers, method="GET")

            logger.debug(f"Downloading image: {chat_id}/{image_id}")

            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                content_type = response.headers.get('Content-Type', '')

                if 'application/json' in content_type:
                    response_data = response.read().decode('utf-8')
                    try:
                        error_data = json.loads(response_data)
                        error_msg = error_data.get('result', {}).get('message', 'Unknown error')
                        logger.error(f"Server returned JSON error: {error_msg}")
                    except:
                        logger.error(f"Server returned unexpected JSON response")
                    return False, b""

                if 'image/' not in content_type:
                    logger.error(f"Unexpected content type: {content_type}")
                    return False, b""

                image_data = response.read()

                if len(image_data) < 8:
                    logger.error(f"Image data too small: {len(image_data)} bytes")
                    return False, b""

                png_signature = b'\x89PNG\r\n\x1a\n'
                if not image_data.startswith(png_signature):
                    logger.error(f"Downloaded data is not a valid PNG image (first bytes: {image_data[:20].hex()})")
                    return False, b""

                logger.debug(f"Downloaded valid PNG image: {len(image_data)} bytes")
                return True, image_data

        except urllib.error.HTTPError as e:
            logger.error(f"HTTP error downloading image {e.code}: {e.reason}")
            try:
                error_body = e.read().decode('utf-8')
                error_data = json.loads(error_body)
                error_msg = error_data.get('result', {}).get('message', error_body)
                logger.error(f"Error details: {error_msg}")
            except:
                pass
            return False, b""

        except urllib.error.URLError as e:
            logger.error(f"URL error downloading image: {e.reason}")
            return False, b""

        except Exception as e:
            logger.error(f"Unexpected error downloading image: {str(e)}")
            return False, b""


api_client = APIClient()
