"""
Google OAuth authentication views for admin panel.
API-based authentication without redirects.
"""
import logging
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view

logger = logging.getLogger(__name__)


@csrf_exempt
@api_view(['POST'])
def google_login_view(request):
    """
    Verify Google ID token and create session.
    
    POST /admin-panel/api/auth/google-login/
    Body: { "id_token": "..." }
    
    Returns:
        - 200: Login successful, HTTPOnly session cookie set
        - 400: Invalid token or missing data
        - 403: Email not authorized
    """
    try:
        # Get ID token from request
        id_token_str = request.data.get('id_token')
        
        logger.info(f"Login attempt - Token received: {id_token_str[:50]}..." if id_token_str else "No token")
        
        if not id_token_str:
            return JsonResponse({
                'success': False,
                'error': 'id_token is required'
            }, status=400)
        
        # Verify the ID token with Google
        try:
            logger.info(f"Verifying token with Google... Client ID: {settings.GOOGLE_CLIENT_ID[:20]}...")
            
            # Verify token and get user info
            idinfo = id_token.verify_oauth2_token(
                id_token_str,
                google_requests.Request(),
                settings.GOOGLE_CLIENT_ID
            )
            
            logger.info(f"Token verified successfully. User info: {idinfo.get('email')}")
            
            # Check token issuer
            if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
                logger.error(f"Invalid issuer: {idinfo['iss']}")
                return JsonResponse({
                    'success': False,
                    'error': 'Invalid token issuer'
                }, status=400)
            
            # Get user info
            email = idinfo.get('email')
            name = idinfo.get('name', '')
            picture = idinfo.get('picture', '')
            
            if not email:
                logger.error("No email in token")
                return JsonResponse({
                    'success': False,
                    'error': 'Email not found in token'
                }, status=400)
            
            # Check if email is in whitelist
            allowed_emails = settings.ADMIN_ALLOWED_EMAILS
            logger.info(f"Checking whitelist. Email: {email}, Allowed: {allowed_emails}")
            
            if allowed_emails and allowed_emails[0]:  # Check if whitelist is configured
                if email not in allowed_emails:
                    logger.warning(f"Unauthorized login attempt from: {email}")
                    return JsonResponse({
                        'success': False,
                        'error': f'Email {email} is not authorized for admin panel'
                    }, status=403)
            
            # Create session
            request.session['admin_authenticated'] = True
            request.session['admin_email'] = email
            request.session['admin_name'] = name
            request.session['admin_picture'] = picture
            request.session.set_expiry(86400)  # 24 hours
            
            logger.info(f"Successful admin login: {email}")
            
            return JsonResponse({
                'success': True,
                'email': email,
                'name': name,
                'picture': picture
            })
            
        except ValueError as e:
            # Invalid token
            logger.error(f"Token verification failed: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': 'Invalid ID token'
            }, status=400)
    
    except Exception as e:
        logger.exception(f"Login error: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Authentication failed'
        }, status=500)


@api_view(['GET'])
def auth_status_view(request):
    """
    Check if user is authenticated.
    
    GET /admin-panel/api/auth/status/
    
    Returns:
        { "authenticated": true/false, "email": "...", "name": "..." }
    """
    if request.session.get('admin_authenticated'):
        return JsonResponse({
            'authenticated': True,
            'email': request.session.get('admin_email', ''),
            'name': request.session.get('admin_name', ''),
            'picture': request.session.get('admin_picture', '')
        })
    
    return JsonResponse({
        'authenticated': False
    })


@csrf_exempt
@api_view(['POST'])
def logout_view(request):
    """
    Logout and clear session.
    
    POST /admin-panel/api/auth/logout/
    
    Returns:
        { "success": true }
    """
    request.session.flush()
    
    return JsonResponse({
        'success': True,
        'message': 'Logged out successfully'
    })
