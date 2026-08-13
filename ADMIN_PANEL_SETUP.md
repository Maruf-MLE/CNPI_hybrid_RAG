# Admin Panel Authentication Setup

## Secure Admin Panel Authentication

This system uses **two separate authentication models**:

### 1. Django System Users (for Django management)
- Used for administrative tasks via `python manage.py createsuperuser`
- Stores data in `admin` database table
- NOT used for the admin panel UI

### 2. Custom AdminUser (for Admin Panel)
- Used for logging into the admin panel at `/admin-panel/`
- Stores data in `admin_users` database table
- **THIS IS WHAT YOU NEED FOR LOGIN**

---

## ✅ Setup Instructions

### Step 1: Set Environment Variables

Add these to your `.env` file:

```env
# Admin panel (Custom User Model)
ADMIN_USERNAME=admin
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=your_secure_password_here

# Optionally, keep separate credentials for the Django admin
DJANGO_SUPERUSER_USERNAME=django_admin
DJANGO_SUPERUSER_PASSWORD=another_secure_password_here
```

### Step 2: Create Default Admin User

Run this command:

```bash
cd G:\CNPI_Hybrid_RAG\cnpi_api
python manage.py createsuperuser
```

Follow the prompts. The system will create a user in the `admin_users` table.

### Step 3: Enable Admin Panel Management

The admin panel uses the custom `AdminUser` model. Once a user is created:

```bash
# Start the server
python manage.py runserver

# Access the admin panel
# URL: http://127.0.0.1:8000/admin-panel/
# Username: admin
# Password: your_secure_password
```

---

## 🔐 Security Best Practices

1. **Never commit passwords to version control**
   - Remove credentials from .env example files
   - Use .env.local for local credentials

2. **Use strong passwords**
   - Minimum 12 characters
   - Mix of letters, numbers, and symbols
   - Example: `P@ssw0rd!2024#Secure`

3. **Rotate passwords regularly**
   ```bash
   python manage.py changepassword admin
   ```

4. **Use composition for multiple environments**
   - Local: .env.local
   - Development: .env.dev
   - Production: .env.prod

---

## 📋 Password Management Commands

Create new admin:  
```bash
python manage.py createsuperuser
```

Change existing password:  
```bash
python manage.py changepassword admin
```

List admin users:
```bash
python manage.py shell -c "from admin_panel.models import AdminUser; print([u.username for u in AdminUser.objects.all()])"
```

### Migration Needed

After these changes, you'll need:

```bash
cd G:\CNPI_Hybrid_RAG\cnpi_api

# Create migrations
python manage.py makemigrations admin_panel

# Apply migrations
python manage.py migrate admin_panel
```

---

## 🛡️ Access Permission Levels

The `AdminUser` model includes a `role` field:

- **Manager**: Full access to all features
- **Editor**: Can create and update documents
- **Viewer**: Read-only access

No database configuration needed — manage roles via Django admin interface.