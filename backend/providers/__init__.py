"""
Provider registry for OAuth/browser-based authentication.

Each provider module should define a `get_provider_config()` function
that returns a config dict for OAuthManager.register_provider().
"""

from typing import Dict, Any, List


def get_all_providers() -> List[Dict[str, Any]]:
    """
    Import and return all available provider configs.
    Add new providers here as they are created.
    """
    providers = []
    
    try:
        from backend.providers.youtube_music import get_provider_config
        providers.append(get_provider_config())
    except ImportError:
        try:
            from providers.youtube_music import get_provider_config
            providers.append(get_provider_config())
        except ImportError:
            pass
    
    # Add future providers here:
    # try:
    #     from backend.providers.twitter import get_provider_config
    #     providers.append(get_provider_config())
    # except ImportError:
    #     pass
    
    return providers


def register_all_providers(oauth_manager):
    """Register all available providers with the OAuthManager."""
    for config in get_all_providers():
        oauth_manager.register_provider(config["name"], config)
