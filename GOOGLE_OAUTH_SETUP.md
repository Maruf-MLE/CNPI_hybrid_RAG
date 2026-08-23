# Google OAuth Setup Guide for Admin Panel

## 🔒 Security Features

Admin panel এখন Google OAuth দিয়ে secure করা হয়েছে:

- ✅ **HTTPOnly Cookies** - JavaScript থেকে access করা যাবে না
- ✅ **Secure Cookies** - শুধু HTTPS এ কাজ করবে (production)
- ✅ **SameSite Protection** - CSRF attack থেকে সুরক্ষা
- ✅ **Email Whitelist** - শুধু authorized emails access পাবে
- ✅ **Session-based Auth** - Server-side token storage

## 📋 Setup Steps

### 1. Google Cloud Console এ যান

1. [Google Cloud Console](https://console.cloud.google.com/) এ যান
2. একটি নতুন project তৈরি করুন অথবা existing project select করুন

### 2. OAuth Consent Screen Configure করুন

1. **APIs & Services** → **OAuth consent screen** এ যান
2. **User Type**: External select করুন
3. **App Information** fill করুন:
   - App name: `CNPI RAG Admin Panel`
   - User support email: আপনার email
   - Developer contact: আপনার email
4. **Scopes**: Add করুন
   - `userinfo.email`
   - `userinfo.profile`
5. **Test users**: আপনার admin email addresses add করুন
6. Save করুন

### 3. OAuth 2.0 Client ID তৈরি করুন

1. **APIs & Services** → **Credentials** এ যান
2. **Create Credentials** → **OAuth 2.0 Client ID** click করুন
3. **Application type**: Web application
4. **Name**: `CNPI RAG Admin Panel`
5. **Authorized JavaScript origins**:
   ```
   http://localhost:3000
   https://your-production-domain.com
   ```
6. **Authorized redirect URIs**:
   ```
   http://localhost:8000/accounts/google/login/callback/
   https://your-production-domain.com/accounts/google/login/callback/
   ```
7. **Create** click করুন
8. **Client ID** এবং **Client Secret** copy করুন

### 4. Environment Variables Setup

আপনার `.env` ফাইলে এই values add করুন:

```env
# Google OAuth
GOOGLE_CLIENT_ID=your-client-id-here.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret-here

# Admin Email Whitelist (comma-separated)
ADMIN_ALLOWED_EMAILS=admin1@gmail.com,admin2@gmail.com,admin3@gmail.com
```

### 5. Database Migration করুন

```bash
cd cnpi_api
python manage.py makemigrations
python manage.py migrate
```

### 6. Dependencies Install করুন

```bash
pip install -r requirements.txt
```

### 7. Django Shell থেকে Site Configure করুন

```bash
python manage.py shell
```

```python
from django.contrib.sites.models import Site
site = Site.objects.get_current()
site.domain = 'localhost:8000'  # Development এর জন্য
# site.domain = 'your-production-domain.com'  # Production এর জন্য
site.name = 'CNPI RAG'
site.save()
exit()
```

### 8. Django Admin থেকে Social App Setup করুন

```bash
# প্রথমে একটি superuser তৈরি করুন
python manage.py createsuperuser
```

1. Django admin এ যান: http://localhost:8000/admin/
2. **Social applications** → **Add** click করুন
3. **Provider**: Google
4. **Name**: Google OAuth
5. **Client id**: আপনার Google Client ID paste করুন
6. **Secret key**: আপনার Google Client Secret paste করুন
7. **Sites**: `example.com` select করে **Chosen sites** তে move করুন
8. **Save** করুন

## 🚀 Testing

### Development এ Test করুন:

1. Backend start করুন:
   ```bash
   cd cnpi_api
   python manage.py runserver
   ```

2. Frontend start করুন:
   ```bash
   cd cnpichat-next
   npm run dev
   ```

3. Browser এ যান: http://localhost:3000/admin2026/
4. "Sign in with Google" button click করুন
5. আপনার Google account দিয়ে login করুন
6. যদি আপনার email whitelist এ থাকে, admin panel access পাবেন

## 🔐 Security Best Practices

### Production Deployment:

1. **HTTPS Enable করুন** - `DEBUG=False` set করলে automatically secure cookies enable হবে
2. **Strong SECRET_KEY** use করুন
3. **Email Whitelist** update করুন - শুধু authorized admins
4. **CORS Settings** tighten করুন - specific domains allow করুন
5. **Regular Security Audits** করুন

### Environment Variables (Production):

```env
DEBUG=False
DJANGO_SECRET_KEY=your-very-strong-secret-key-here
GOOGLE_CLIENT_ID=your-production-client-id
GOOGLE_CLIENT_SECRET=your-production-client-secret
ADMIN_ALLOWED_EMAILS=real-admin1@domain.com,real-admin2@domain.com
```

## 🐛 Troubleshooting

### Issue: "Redirect URI mismatch"
**Solution**: Google Cloud Console এ আপনার redirect URI ঠিক মতো add করেছেন কিনা check করুন।

### Issue: "Access denied" after login
**Solution**: আপনার email `ADMIN_ALLOWED_EMAILS` এ আছে কিনা check করুন।

### Issue: "Site matching query does not exist"
**Solution**: Django shell থেকে Site configure করুন (Step 7)।

### Issue: CSRF verification failed
**Solution**: `CORS_ALLOW_CREDENTIALS=True` এবং `SESSION_COOKIE_SAMESITE='Lax'` settings check করুন।

## 📝 Notes

- Development এ `localhost:8000` এবং `localhost:3000` দুটোই configure করতে হবে
- Production এ শুধু আপনার actual domain use করবেন
- Test users শুধু OAuth consent screen "Testing" mode এ থাকাকালীন কাজ করবে
- Production এ যাওয়ার আগে OAuth app "Published" করতে হবে

## 🔄 Migration from Password Auth

পুরনো password-based authentication সম্পূর্ণভাবে replace হয়ে গেছে Google OAuth দিয়ে। এখন:

- ❌ কোনো password field নেই
- ✅ Google "Sign in" button আছে
- ✅ HTTPOnly session cookies use হচ্ছে
- ✅ Email-based authorization হচ্ছে

## 📚 Additional Resources

- [Django Allauth Documentation](https://django-allauth.readthedocs.io/)
- [Google OAuth 2.0 Guide](https://developers.google.com/identity/protocols/oauth2)
- [Django Security Best Practices](https://docs.djangoproject.com/en/stable/topics/security/)
