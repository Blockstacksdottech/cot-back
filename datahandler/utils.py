from decouple import config

def get_proxies():
    """
    Returns the proxies dictionary for the requests library using credentials from environment variables.
    """
    proxy_host = config('PROXY_HOST', default=None)
    proxy_port = config('PROXY_PORT', default=None)
    proxy_user = config('PROXY_USER', default=None)
    proxy_pass = config('PROXY_PASS', default=None)

    if all([proxy_host, proxy_port, proxy_user, proxy_pass]):
        proxy_url = f"http://{proxy_user}:{proxy_pass}@{proxy_host}:{proxy_port}"
        return {
            "http": proxy_url,
            "https": proxy_url,
        }
    return None
