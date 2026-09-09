"""
Django settings for kb_project project.
"""

from pathlib import Path

# ---------------------------------------------------------------------------
# Base Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------------
SECRET_KEY = 'django-insecure-epa9_q-l7yrhr1ap!75y9_kyak7*d)sqv($q6t%@wazao2dsq('

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['*']


# ---------------------------------------------------------------------------
# Application Definition
# ---------------------------------------------------------------------------
INSTALLED_APPS = [
    # Django built-ins
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',

    # Third-party
    'django_filters',

    # KB Foundation apps
    'accounts',
    'donors',
    'expenditures',
    'scholarships',
    'reports',
    'core',           # Phase 1: Public-facing homepage & shared views
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',

    # Phase 2: Must come AFTER AuthenticationMiddleware so request.user is set.
    # Redirects users with requires_password_change=True to the change-password page.
    'accounts.middleware.ForcePasswordChangeMiddleware',

    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'kb_project.urls'


# ---------------------------------------------------------------------------
# Templates  — point Django at the global /templates folder
# ---------------------------------------------------------------------------
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        # Global templates directory at project root
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.unread_notifications',
            ],
        },
    },
]

WSGI_APPLICATION = 'kb_project.wsgi.application'


# ---------------------------------------------------------------------------
# Database — MySQL (kb_foundation_db)
# Create this database manually: CREATE DATABASE kb_foundation_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
# ---------------------------------------------------------------------------
import os

# Check if we are running on Render (Render sets 'RENDER' environment variable to 'true')
if 'RENDER' in os.environ:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
else:
    # Your local XAMPP MySQL configuration
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': 'kb_foundation_db',
            'USER': 'root',
            'PASSWORD': 'Hollister@18',
            'HOST': 'localhost',
            'PORT': '3306',
            'OPTIONS': {
                'charset': 'utf8mb4',
                'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            },
        }
    }

# ---------------------------------------------------------------------------
# Custom User Model  ← CRITICAL: must be set before first migration
# ---------------------------------------------------------------------------
AUTH_USER_MODEL = 'accounts.CustomUser'


# ---------------------------------------------------------------------------
# Password Validation
# ---------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# ---------------------------------------------------------------------------
# Internationalisation
# ---------------------------------------------------------------------------
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Lagos'   # WAT — adjust if team is in a different TZ
USE_I18N = True
USE_TZ = True


# ---------------------------------------------------------------------------
# Static Files
# ---------------------------------------------------------------------------
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']


# ---------------------------------------------------------------------------
# Media Files (user uploads — documents, images)
# ---------------------------------------------------------------------------
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'


# ---------------------------------------------------------------------------
# Default primary key field type
# ---------------------------------------------------------------------------
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# ---------------------------------------------------------------------------
# Login / Logout redirects
# ---------------------------------------------------------------------------
LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/reports/dashboard/'
LOGOUT_REDIRECT_URL = '/accounts/login/'


# ---------------------------------------------------------------------------
# Authentication Backends  — Phase 2.5
# ---------------------------------------------------------------------------
# Our custom backend is listed FIRST so it runs before Django's default.
# It resolves the login credential against username, email, AND unique_id.
# Django's ModelBackend is kept as a second-level fallback for Django Admin
# compatibility (management commands, shell, etc.).
AUTHENTICATION_BACKENDS = [
    'accounts.backends.EmailOrUniqueIdModelBackend',  # email / unique_id / username
    'django.contrib.auth.backends.ModelBackend',       # fallback (Django Admin shell)
]


# ---------------------------------------------------------------------------
# Email Configuration — Phase 10: Gmail SMTP
# ---------------------------------------------------------------------------
# How to generate a Google App Password (required — standard Gmail passwords won't work):
#   1. Go to your Google Account → Security → 2-Step Verification (must be ON).
#   2. At the bottom of the 2-Step Verification page, click "App passwords".
#   3. Select app: "Mail", device: "Windows Computer" → Click Generate.
#   4. Copy the 16-character password (e.g. "abcd efgh ijkl mnop") — remove spaces.
#   5. Paste the 16 characters below as EMAIL_HOST_PASSWORD.
#
# IMPORTANT: Never commit real credentials to version control. Use environment
# variables (os.environ.get) or a .env file in production.
# ---------------------------------------------------------------------------
EMAIL_BACKEND     = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST        = 'smtp.gmail.com'
EMAIL_PORT        = 465
EMAIL_USE_SSL     = True
EMAIL_USE_TLS     = False
EMAIL_HOST_USER     = 'olatundeadunfe@gmail.com'   # ← Replace with your Gmail address
EMAIL_HOST_PASSWORD = 'hfktzezuscktrhxs'  # ← Replace with App Password (no spaces)
DEFAULT_FROM_EMAIL = 'noreply@kbfoundation.org'
EMAIL_SUBJECT_PREFIX = '[KB Foundation] '

# ---------------------------------------------------------------------------
# Messages — map Django levels to Bootstrap 5 alert classes
# ---------------------------------------------------------------------------
from django.contrib.messages import constants as messages_constants

MESSAGE_TAGS = {
    messages_constants.DEBUG:   'secondary',
    messages_constants.INFO:    'info',
    messages_constants.SUCCESS: 'success',
    messages_constants.WARNING: 'warning',
    messages_constants.ERROR:   'danger',   # Bootstrap uses 'danger', not 'error'
}

# ---------------------------------------------------------------------------
# SSL Bypass — Phase 16
# ---------------------------------------------------------------------------
# Antivirus/Firewall software (e.g. Avast, Norton, Kaspersky, Windows Defender
# Network Inspection) intercepts outbound SSL connections and re-signs them
# with a local CA certificate that Python's ssl module does not trust,
# causing [SSL: CERTIFICATE_VERIFY_FAILED] on smtp.gmail.com port 465.
#
# This monkey-patch tells Python's ssl module to skip certificate verification
# entirely for the duration of this process, allowing the SMTP handshake to
# succeed through the local SSL inspector.
#
# WARNING: Only appropriate for development/local use. Remove before deploying
# to a public/production server where certificate validation is mandatory.
# ---------------------------------------------------------------------------
import ssl
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass   # Python version does not support this — skip silently
else:
    ssl._create_default_https_context = _create_unverified_https_context
    ssl.create_default_context = _create_unverified_https_context