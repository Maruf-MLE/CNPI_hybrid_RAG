"""
Authentication middleware for admin panel.
Session-based authentication with Google OAuth.
"""
from django.http import JsonResponse


class AdminAuthenticationMiddleware:
    """
    Middleware to protect admin panel API endpoints.
    Requires Google OAuth session authentication.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Check if the request is for admin panel API
        if request.path.startswith('/admin-panel/api/'):
            # Allow auth endpoints without authentication
            auth_endpoints = [
                '/admin-panel/api/auth/google-login/',
                '/admin-panel/api/auth/status/',
                '/admin-panel/api/auth/logout/',
            ]
            
            if request.path in auth_endpoints:
                return self.get_response(request)
            
            # Check if user has valid session
            if not request.session.get('admin_authenticated'):
                return JsonResponse({
                    'error': 'Authentication required',
                    'detail': 'Please login with Google to access admin panel'
                }, status=401)
        
        response = self.get_response(request)
        return response
