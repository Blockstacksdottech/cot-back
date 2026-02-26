from decouple import config

def get_proxies(session_id=None):
    """
    Returns the proxies dictionary for the requests library using credentials from environment variables.
    If session_id is provided, it appends it to the proxy user for sticky sessions (IPRoyal feature).
    """
    proxy_host = config('PROXY_HOST', default=None)
    proxy_port = config('PROXY_PORT', default=None)
    proxy_user = config('PROXY_USER', default=None)
    proxy_pass = config('PROXY_PASS', default=None)

    if all([proxy_host, proxy_port, proxy_user, proxy_pass]):
        if session_id:
            # For IPRoyal, appending session parameters to the password triggers a sticky session
            # Format: _session-8charID_lifetime-duration
            proxy_pass = f"{proxy_pass}_session-{session_id}_lifetime-10m"
        
        proxy_url = f"http://{proxy_user}:{proxy_pass}@{proxy_host}:{proxy_port}"
        return {
            "http": proxy_url,
            "https": proxy_url,
        }
    return None
