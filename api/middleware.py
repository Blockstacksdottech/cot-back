import requests
import time
from django.conf import settings
from django.http import HttpResponseForbidden, JsonResponse
from django.core.cache import cache

class LicenseCheckMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.license_url = getattr(settings, 'LICENSE_CHECK_URL', None)
        self.admin_token = getattr(settings, 'LICENSE_ADMIN_TOKEN', None)
        self.cache_timeout = 300  # 5 minutes cache

    def __call__(self, request):
        # 1. Bypass check (Admin Token)
        # Check Header 'X-Admin-Bypass' or Query Param 'admin_bypass'
        bypass_token = request.headers.get('X-Admin-Bypass') or request.GET.get('admin_bypass')
        
        if self.admin_token and bypass_token == self.admin_token:
            return self.get_response(request)

        # 2. Check License Status
        if self.license_url:
            is_active = self.check_license_status()
            if not is_active:
                response = JsonResponse(
                    {"error": "Service Temporarily Unavailable", "code": "MAINTENANCE_MODE"}, 
                    status=503
                )
                response['X-License-Status'] = 'inactive'
                return response

        response = self.get_response(request)
        response['X-License-Status'] = 'active'
        return response

    def check_license_status(self):
        # Allow if no URL configured
        if not self.license_url:
            return True

        # Check Cache
        cached_status = cache.get('license_status')
        if cached_status is not None:
            return cached_status

        # Fetch Remote Status
        try:
            response = requests.get(self.license_url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                status = data.get('status', 'active')
                is_active = (status == 'active')
                
                # Cache the result
                cache.set('license_status', is_active, self.cache_timeout)
                return is_active
            else:
                print(f"[LICENSE] Unexpected status code: {response.status_code}")
        except Exception as e:
            # On error, log it and fail open to avoid downtime
            print(f"[LICENSE] Check failed: {e}")
            return True 
            
        return True
