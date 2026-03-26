"""
Platform keychain helpers for secret storage.

Tries the ``keyring`` library first (works on macOS Keychain, Windows
Credential Vault, and freedesktop Secret Service / KWallet on Linux).
Falls back to the existing file-based storage when ``keyring`` is not
available or the backend fails.
"""

from .logger import logger

SERVICE_NAME = "vibe5d-blender"
_KEY_API_KEY = "provider_api_key"

_keyring = None
_keyring_available = False

try:
    import keyring as _keyring
    # Probe the backend to make sure it's functional
    _keyring.get_password(SERVICE_NAME, "__probe__")
    _keyring_available = True
    logger.debug("Keyring backend available for secret storage")
except Exception:
    _keyring_available = False
    logger.debug("Keyring not available — secrets will be stored in config files")


def is_keychain_available() -> bool:
    """Return *True* if platform keychain storage is usable."""
    return _keyring_available


def store_api_key(api_key: str) -> bool:
    """Store the provider API key in the platform keychain.

    Returns *True* on success, *False* if the keychain is unavailable or
    the write failed.
    """
    if not _keyring_available or not _keyring:
        return False
    try:
        _keyring.set_password(SERVICE_NAME, _KEY_API_KEY, api_key)
        logger.debug("API key stored in platform keychain")
        return True
    except Exception as e:
        logger.warning(f"Failed to store API key in keychain: {e}")
        return False


def load_api_key() -> str:
    """Load the provider API key from the platform keychain.

    Returns the key string, or ``""`` if unavailable.
    """
    if not _keyring_available or not _keyring:
        return ""
    try:
        secret = _keyring.get_password(SERVICE_NAME, _KEY_API_KEY)
        return secret or ""
    except Exception as e:
        logger.warning(f"Failed to load API key from keychain: {e}")
        return ""


def delete_api_key() -> bool:
    """Remove the provider API key from the platform keychain."""
    if not _keyring_available or not _keyring:
        return False
    try:
        _keyring.delete_password(SERVICE_NAME, _KEY_API_KEY)
        logger.debug("API key removed from platform keychain")
        return True
    except Exception as e:
        logger.debug(f"Failed to delete API key from keychain: {e}")
        return False
