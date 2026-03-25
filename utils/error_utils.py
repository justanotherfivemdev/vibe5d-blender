from typing import List, Dict, Any

from .logger import logger


def format_error_message(error_code: str, user_message: str, suggestions: List[str] = None,
                         retryable: bool = True, technical_info: str = None) -> str:
    return user_message


def extract_error_type(error_message: str) -> str:
    try:
        error_lower = error_message.lower()

        if any(term in error_lower for term in ['connection', 'network', 'timeout', 'unreachable']):
            return 'network'

        if any(term in error_lower for term in ['auth', 'license', 'credential', 'unauthorized']):
            return 'authentication'

        if any(term in error_lower for term in ['rate limit', 'quota', 'too many requests']):
            return 'rate_limit'

        if any(term in error_lower for term in ['syntax', 'indentation', 'nameerror', 'typeerror']):
            return 'code_error'

        if any(term in error_lower for term in ['permission', 'access denied', 'forbidden']):
            return 'permission'

        if any(term in error_lower for term in ['service', 'maintenance', 'unavailable']):
            return 'service'

        return 'general'

    except Exception as e:
        logger.error(f"Error extracting error type: {e}")
        return 'general'


def get_error_severity(error_code: str) -> str:
    try:

        critical_errors = {
            'AUTHORIZATION_FAILED', 'SYSTEM_MISCONFIGURED',
            'OUTDATED_CLIENT', 'FEATURE_NOT_AVAILABLE'
        }


        high_errors = {
            'MAINTENANCE_MODE', 'AI_SERVICE_UNAVAILABLE',
            'INTERNAL_SERVER_ERROR', 'DB_ERROR'
        }


        medium_errors = {
            'RATE_LIMIT', 'INVALID_CODE_GENERATED',
            'INVALID_REQUEST', 'NO_ACTIONS_GENERATED'
        }


        low_errors = {
            'TIMEOUT', 'INTERNAL_ERROR', 'LLM_ERROR',
            'CLIENT_ERROR'
        }

        if error_code in critical_errors:
            return 'critical'
        elif error_code in high_errors:
            return 'high'
        elif error_code in medium_errors:
            return 'medium'
        elif error_code in low_errors:
            return 'low'
        else:
            return 'medium'

    except Exception as e:
        logger.error(f"Error determining error severity: {e}")
        return 'medium'


def should_show_retry_button(error_code: str, retryable: bool) -> bool:
    try:

        no_retry_errors = {
            'FEATURE_NOT_AVAILABLE', 'PLAN_LIMIT_EXCEEDED',
            'AUTHORIZATION_FAILED', 'SYSTEM_MISCONFIGURED'
        }

        if error_code in no_retry_errors:
            return False

        always_retry_errors = {
            'TIMEOUT', 'AI_SERVICE_UNAVAILABLE',
            'RATE_LIMIT', 'DB_ERROR'
        }

        if error_code in always_retry_errors:
            return True

        return retryable

    except Exception as e:
        logger.error(f"Error determining retry button visibility: {e}")
        return retryable


def create_chat_error_message(error_type: str, error_message: str, suggestions: List[str] = None) -> str:
    try:

        formatted_msg = f"❌ **{error_type}**\n\n"

        formatted_msg += f"{error_message}\n\n"

        return formatted_msg

    except Exception as e:
        logger.error(f"Error creating chat error message: {e}")
        return f"❌ **{error_type}:** {error_message}"


def create_error_context(error_data) -> Dict[str, Any]:
    try:
        if isinstance(error_data, dict):
            error_code = error_data.get('code', 'UNKNOWN')
            user_message = error_data.get('user_message', 'An error occurred')
            suggestions = []
            retryable = error_data.get('retryable', True)
            technical_info = error_data.get('technical_info', '')
        else:

            error_code = str(error_data)

            if error_code.lower().startswith('error'):
                user_message = error_code
            else:
                user_message = f"{error_code}"
            suggestions = []
            retryable = True
            technical_info = ''

        return {
            'code': error_code,
            'user_message': user_message,
            'suggestions': suggestions,
            'retryable': retryable,
            'technical_info': technical_info,
            'severity': get_error_severity(error_code),
            'error_type': extract_error_type(user_message),
            'show_retry': should_show_retry_button(error_code, retryable),
            'formatted_message': format_error_message(
                error_code, user_message, suggestions, retryable, technical_info
            )
        }

    except Exception as e:
        logger.error(f"Error creating error context: {e}")
        return {
            'code': 'UNKNOWN',
            'user_message': 'An unexpected error occurred',
            'suggestions': ['Try again in a moment'],
            'retryable': True,
            'technical_info': str(e),
            'severity': 'medium',
            'error_type': 'general',
            'show_retry': True,
            'formatted_message': 'An unexpected error occurred'
        }
