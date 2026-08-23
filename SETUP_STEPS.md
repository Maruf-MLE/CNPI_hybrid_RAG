# 🚀 Google OAuth Setup - Quick Start Guide

## ✅ যা ইতিমধ্যে হয়ে গেছে:

- ✅ `django-allauth` installed
- ✅ Database migrations completed
- ✅ Backend code configured
- ✅ Frontend updated
- ✅ Middleware setup complete
- ✅ HTTPOnly cookies enabled

## 📝 এখন আপনাকে করতে হবে:

### Step 1: `.env` ফাইল update করুন

আপনার `.env` ফাইলে এই lines add করুন:

```env
# Google OAuth Credentials
GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-google-client-secret

# Admin Email Whitelist (comma-separated, no spaces)
ADMIN_ALLOWED_EMAILS=your-email@gmail.com,another-admin@gmail.com
```

### Step 2: Django Superuser তৈরি করুন

Terminal এ run করুন:

```bash
cd cnpi_api
python manage.py createsuperuser
```

যখন prompt আসবে:
- **Username**: যেকোনো username (যেমন: admin)
- **Email**: আপনার email
- **Password**: একটা strong password দিন

### Step 3: Django Admin থেকে Site Configure করুন

1. Django server চালু করুন:
```bash
python manage.py runserver
```

2. Browser এ যান: http://localhost:8000/admin/

3. আপনার superuser credentials দিয়ে login করুন

4. **Sites** section এ click করুন

5. `example.com` এ click করুন এবং edit করুন:
   - **Domain name**: `localhost:8000` (development এর জন্য)
   - **Display name**: `CNPI RAG`
   - **Save** করুন

### Step 4: Google Cloud Console Setup

#### 4.1 Google Cloud Console এ যান

https://console.cloud.google.com/

#### 4.2 New Project তৈরি করুন (optional)

- **Project name**: `CNPI RAG Admin`
- **Create** click করুন

#### 4.3 OAuth Consent Screen Configure করুন

1. **APIs & Services** → **OAuth consent screen**
2. **User Type**: External
3. **Create** click করুন
4. Fill করুন:
   - **App name**: `CNPI RAG Admin Panel`
   - **User support email**: আপনার email
   - **Developer contact**: আপনার email
5. **Save and Continue**
6. **Scopes** page এ **Save and Continue** (default scopes ঠিক আছে)
7. **Test users** page এ:
   - **ADD USERS** click করুন
   - আপনার admin email add করুন
   - **Save and Continue**
8. **Summary** page এ **Back to Dashboard**

#### 4.4 OAuth 2.0 Client ID তৈরি করুন

1. **APIs & Services** → **Credentials**
2. **+ CREATE CREDENTIALS** → **OAuth client ID**
3. **Application type**: Web application
4. **Name**: `CNPI RAG Admin Panel`
5. **Authorized JavaScript origins**:
   ```
   http://localhost:8000
   http://localhost:3000
   ```
6. **Authorized redirect URIs**:
   ```
   http://localhost:8000/accounts/google/login/callback/
   ```
7. **CREATE** click করুন
8. **Client ID** এবং **Client secret** copy করে `.env` ফাইলে paste করুন

### Step 5: Django Admin এ Social App Setup

1. Django admin এ ফিরে যান: http://localhost:8000/admin/

2. **Social applications** → **Add social application**

3. Fill করুন:
   - **Provider**: Google
   - **Name**: Google OAuth
   - **Client id**: আপনার Google Client ID paste করুন
   - **Secret key**: আপনার Google Client Secret paste করুন
   - **Sites**: "localhost:8000" (বা যা আপনি step 3 এ set করেছেন) select করে **→** arrow click করে **Chosen sites** তে move করুন
   - **Save** করুন

### Step 6: Test করুন

#### Backend চালু করুন:
```bash
cd cnpi_api
python manage.py runserver
```

#### Frontend চালু করুন (নতুন terminal):
```bash
cd cnpichat-next
npm run dev
```

#### Browser এ test করুন:

1. http://localhost:3000/admin2026/ এ যান
2. **"Sign in with Google"** button দেখতে পাবেন
3. Click করুন
4. Google account select করুন
5. Permission allow করুন
6. Admin panel এ redirect হবে!

## 🎉 Success!

যদি সবকিছু ঠিক থাকে, তাহলে:
- ✅ Google login button দেখবেন
- ✅ Google দিয়ে login করতে পারবেন
- ✅ Header এ আপনার email এবং logout button দেখবেন
- ✅ Admin panel এর সব features কাজ করবে

## 🔧 Troubleshooting

### Issue 1: "Redirect URI mismatch" error

**Solution**: Google Cloud Console এ গিয়ে check করুন redirect URI ঠিক মতো add করেছেন কিনা:
```
http://localhost:8000/accounts/google/login/callback/
```

### Issue 2: "Access denied" after login

**Solution**: 
1. `.env` ফাইলে `ADMIN_ALLOWED_EMAILS` তে আপনার email আছে কিনা check করুন
2. Email গুলোর মধ্যে comma আছে কিনা, space নেই তো?
   ```env
   ADMIN_ALLOWED_EMAILS=email1@gmail.com,email2@gmail.com
   ```

### Issue 3: "Site matching query does not exist"

**Solution**: Django shell থেকে manually site configure করুন:

```bash
python manage.py shell
```

```python
from django.contrib.sites.models import Site
site = Site.objects.get_current()
site.domain = 'localhost:8000'
site.name = 'CNPI RAG'
site.save()
exit()
```

### Issue 4: Server crashes with module errors

**Solution**: Dependencies install করুন:
```bash
pip install -r requirements.txt
```

## 📚 Important Files Modified

1. **Backend:**
   - `cnpi_api/cnpi_api/settings.py` - OAuth configuration
   - `cnpi_api/admin_panel/middleware.py` - Authentication middleware
   - `cnpi_api/admin_panel/views.py` - Auth status endpoint
   - `cnpi_api/admin_panel/urls.py` - Auth routes
   - `requirements.txt` - Added django-allauth

2. **Frontend:**
   - `cnpichat-next/app/admin2026/page.tsx` - Google OAuth UI

3. **Config:**
   - `.env.example` - Added Google OAuth variables

## 🔐 Security Checklist

- ✅ HTTPOnly cookies enabled
- ✅ Secure cookies (HTTPS only in production)
- ✅ SameSite CSRF protection
- ✅ Email whitelist authorization
- ✅ Session-based authentication
- ✅ XSS protection headers
- ✅ Public chat API unaffected
- ✅ Admin API fully protected

## 📖 Additional Documentation

বিস্তারিত setup guide এর জন্য দেখুন: `GOOGLE_OAUTH_SETUP.md`

---

**Need Help?** 
- Documentation: [Django Allauth](https://django-allauth.readthedocs.io/)
- Google OAuth: [Google Identity](https://developers.google.com/identity/protocols/oauth2)
