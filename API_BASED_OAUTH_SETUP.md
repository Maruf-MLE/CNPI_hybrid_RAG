# 🚀 Professional Google OAuth Setup Guide (API-based, No Redirect)

## ✅ কী করা হয়েছে:

### Backend (Django):
- ✅ Django Allauth সম্পূর্ণ remove করা হয়েছে
- ✅ `google-auth` library install করা হয়েছে (token verification)
- ✅ 3টা API endpoint তৈরি করা হয়েছে (login, status, logout)
- ✅ Session-based authentication middleware
- ✅ HTTPOnly cookies configured
- ✅ Email whitelist authorization

### Frontend (Next.js):
- ✅ Google Sign-In SDK integrated
- ✅ API-based authentication flow
- ✅ No redirects - সব frontend থেকে হয়
- ✅ Automatic cookie handling

## 🏗️ Architecture Flow:

```
User clicks "Sign in with Google"
         ↓
Google popup opens (frontend only)
         ↓
User logs in with Google
         ↓
Google returns ID token to frontend
         ↓
Frontend POST করে backend API এ: /admin-panel/api/auth/google-login/
         ↓
Backend verify করে token (Google API দিয়ে)
         ↓
Backend check করে email whitelist
         ↓
Backend creates session এবং HTTPOnly cookie set করে
         ↓
Frontend automatically cookie পায়
         ↓
সব future API calls automatically এই cookie include করে
```

## 📝 Setup Steps:

### Step 1: Google Cloud Console Setup

#### 1.1 Go to Google Cloud Console
https://console.cloud.google.com/

#### 1.2 Create or Select Project
- **New Project**: Click "New Project" → Name: "CNPI RAG Admin"

#### 1.3 Enable Google+ API
1. **APIs & Services** → **Library**
2. Search for "Google+ API"
3. Click **Enable**

#### 1.4 Create OAuth 2.0 Client ID

1. **APIs & Services** → **Credentials**
2. Click **+ CREATE CREDENTIALS** → **OAuth client ID**
3. If prompted, configure OAuth consent screen:
   - **User Type**: External
   - **App name**: CNPI RAG Admin Panel
   - **User support email**: Your email
   - **Developer contact**: Your email
   - **Test users**: Add your admin email(s)
   - Save

4. Create OAuth Client ID:
   - **Application type**: Web application
   - **Name**: CNPI RAG Admin Panel
   - **Authorized JavaScript origins**:
     ```
     http://localhost:3000
     http://localhost:8000
     https://your-production-domain.com
     ```
   - **Authorized redirect URIs**: 
     ```
     http://localhost:3000/admin2026
     https://your-production-domain.com/admin2026
     ```
     ⚠️ **Important**: এগুলো শুধু fallback এর জন্য। আসলে কোনো redirect হবে না!

5. Click **CREATE**
6. Copy **Client ID** (শুধু Client ID দরকার, Secret দরকার নেই!)

### Step 2: Backend Configuration

#### 2.1 Update `.env` file:

```env
# Google OAuth
GOOGLE_CLIENT_ID=your-actual-client-id.apps.googleusercontent.com

# Admin Email Whitelist (comma-separated, no spaces)
ADMIN_ALLOWED_EMAILS=your-email@gmail.com,admin2@example.com

# Django Secret
DJANGO_SECRET_KEY=your-strong-secret-key-here
DEBUG=True
```

#### 2.2 Install Dependencies:

```bash
cd cnpi_api
pip install google-auth
```

অথবা:

```bash
pip install -r requirements.txt
```

### Step 3: Frontend Configuration

#### 3.1 Create `.env.local` file in `cnpichat-next/`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_GOOGLE_CLIENT_ID=your-actual-client-id.apps.googleusercontent.com
```

⚠️ **Important**: Frontend এবং Backend এ **same Client ID** use করুন!

### Step 4: Test করুন

#### 4.1 Backend Start করুন:

```bash
cd cnpi_api
python manage.py runserver
```

#### 4.2 Frontend Start করুন (নতুন terminal):

```bash
cd cnpichat-next
npm run dev
```

#### 4.3 Browser এ Test করুন:

1. Go to: http://localhost:3000/admin2026/
2. আপনি একটা **Google Sign-In button** দেখবেন (blue button)
3. Button click করুন
4. Google popup খুলবে (কোনো redirect নেই!)
5. আপনার Google account select করুন
6. Login successful হলে admin panel দেখাবে
7. Header এ আপনার email এবং logout button থাকবে

## 🔐 Security Features:

| Feature | Status | Details |
|---------|--------|---------|
| **No Backend Redirect** | ✅ | সব কিছু frontend popup এ হয় |
| **HTTPOnly Cookies** | ✅ | JavaScript access করতে পারবে না |
| **Secure Cookies** | ✅ | Production এ শুধু HTTPS |
| **SameSite Protection** | ✅ | CSRF attack prevention |
| **Token Verification** | ✅ | Backend এ Google verify করে |
| **Email Whitelist** | ✅ | শুধু authorized emails |
| **Session-based** | ✅ | Server-side storage |
| **24h Session Expiry** | ✅ | Auto logout |

## 🔧 API Endpoints:

### 1. Login (Frontend calls this after Google popup):
```
POST /admin-panel/api/auth/google-login/
Body: { "id_token": "eyJhbGc..." }
Response: { "success": true, "email": "user@gmail.com" }
Sets: HTTPOnly session cookie
```

### 2. Check Status:
```
GET /admin-panel/api/auth/status/
Response: { "authenticated": true, "email": "user@gmail.com" }
```

### 3. Logout:
```
POST /admin-panel/api/auth/logout/
Response: { "success": true }
Clears: Session cookie
```

## 🐛 Troubleshooting:

### Issue 1: "Invalid Client ID" error

**Solution**: 
1. Check `.env` তে Client ID ঠিক আছে কিনা
2. Frontend এর `.env.local` তে same Client ID আছে কিনা
3. Client ID copy করার সময় extra space আছে কিনা check করুন

### Issue 2: Google button দেখা যাচ্ছে না

**Solution**:
1. Browser console check করুন (F12)
2. `NEXT_PUBLIC_GOOGLE_CLIENT_ID` set করা আছে কিনা check করুন
3. `.env.local` file create করেছেন কিনা
4. Server restart করুন: Ctrl+C তারপর `npm run dev`

### Issue 3: "Access denied" after login

**Solution**:
1. `.env` ফাইলে `ADMIN_ALLOWED_EMAILS` তে আপনার email আছে কিনা
2. Email এর মধ্যে space নেই তো? (comma দিয়ে separate, space নেই)
   ```env
   ADMIN_ALLOWED_EMAILS=email1@gmail.com,email2@gmail.com
   ```

### Issue 4: "Authentication required" error

**Solution**:
1. Cookies enabled আছে কিনা browser এ
2. Incognito mode এ test করুন
3. CORS সঠিক ভাবে configured আছে কিনা

### Issue 5: Backend crashes

**Solution**:
```bash
pip install google-auth
python manage.py runserver
```

## 📊 Key Differences from Previous Implementation:

| Feature | Old (Django Allauth) | New (API-based) |
|---------|---------------------|-----------------|
| **Redirect** | ✅ Backend redirect হতো | ❌ কোনো redirect নেই |
| **Flow** | Django managed | Frontend managed |
| **Dependencies** | django-allauth | google-auth (lighter) |
| **Setup Complexity** | High (Site, Social App) | Low (শুধু Client ID) |
| **User Experience** | Backend redirect | Google popup (smooth) |
| **Secret Required** | ✅ Client Secret | ❌ শুধু Client ID |

## 🎯 Production Checklist:

### Environment Variables:
```env
# Backend (.env)
DEBUG=False
GOOGLE_CLIENT_ID=your-production-client-id
ADMIN_ALLOWED_EMAILS=real-admin1@company.com,real-admin2@company.com
DJANGO_SECRET_KEY=very-strong-secret-key

# Frontend (.env.local)
NEXT_PUBLIC_API_URL=https://your-backend-domain.com
NEXT_PUBLIC_GOOGLE_CLIENT_ID=your-production-client-id
```

### Google Cloud Console:
1. Update **Authorized JavaScript origins**:
   ```
   https://your-frontend-domain.com
   ```
2. Update **Authorized redirect URIs**:
   ```
   https://your-frontend-domain.com/admin2026
   ```
3. **OAuth Consent Screen**: Publish করুন (Testing থেকে Production এ)

### Security:
- ✅ HTTPS enable করুন
- ✅ CORS settings tighten করুন (specific domains)
- ✅ Rate limiting add করুন
- ✅ Regular security audits

## 🎉 Success Indicators:

যখন সব ঠিক থাকবে:
- ✅ http://localhost:3000/admin2026/ এ Google Sign-In button দেখবেন
- ✅ Button click করলে Google popup খুলবে (কোনো page redirect নেই!)
- ✅ Login করার পর admin panel instantly load হবে
- ✅ Header এ আপনার email দেখবেন
- ✅ Logout button click করলে instant logout হবে
- ✅ Browser console এ কোনো error নেই

## 📚 Files Changed:

### Backend:
- `cnpi_api/cnpi_api/settings.py` - Allauth remove, security config
- `cnpi_api/admin_panel/auth_views.py` - **NEW** - Login API endpoints
- `cnpi_api/admin_panel/middleware.py` - Session-based auth
- `cnpi_api/admin_panel/urls.py` - New auth routes
- `cnpi_api/cnpi_api/urls.py` - Remove allauth URLs
- `requirements.txt` - google-auth added

### Frontend:
- `cnpichat-next/app/admin2026/page.tsx` - Google Sign-In SDK
- `cnpichat-next/.env.local.example` - **NEW** - Environment template

### Documentation:
- `.env.example` - Updated
- `API_BASED_OAUTH_SETUP.md` - **This file**

## 💡 How It Works:

1. **Frontend loads** → Google SDK script loads
2. **User clicks button** → Google popup opens (no redirect!)
3. **User logs in** → Google gives ID token to frontend
4. **Frontend sends token** → Backend via `/api/auth/google-login/`
5. **Backend verifies** → Checks with Google if token is valid
6. **Backend checks whitelist** → Is this email allowed?
7. **Backend creates session** → Sets HTTPOnly cookie
8. **Frontend gets cookie** → Automatically included in all requests
9. **All API calls** → Use this cookie for authentication
10. **No manual token handling** → Browser handles everything!

---

**Need Help?**
- Google OAuth Documentation: https://developers.google.com/identity/gsi/web
- Django Sessions: https://docs.djangoproject.com/en/stable/topics/http/sessions/
- HTTPOnly Cookies: https://owasp.org/www-community/HttpOnly
