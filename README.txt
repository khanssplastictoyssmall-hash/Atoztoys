ATOZ TOYS V12 - FLAT ROOT DEPLOYMENT

IMPORTANT:
- Every file is in the ROOT of this ZIP. No folders are required.
- This version includes index.html, admin.html, CSS, JS, Flask API, PostgreSQL support, categories/sub-categories, products, ads/posters/banners, cart, search, footer, policies/help links, and store settings.
- Admin changes are saved in PostgreSQL, so they do not require editing GitHub files.

RENDER ENVIRONMENT VARIABLES:
DATABASE_URL = your PostgreSQL Internal Database URL
SECRET_KEY = a long random secret
ADMIN_USER = your chosen admin username
ADMIN_PASSWORD = your strong admin password

START COMMAND:
gunicorn app:app

After deployment:
1. Open https://YOUR-SITE.onrender.com/admin
2. Login with ADMIN_USER / ADMIN_PASSWORD.
3. Add/edit products, categories, ads and store text from the Admin Panel.

NOTE:
The checkout button is a front-end placeholder until you connect your preferred payment/order provider. Do not put payment secrets in GitHub.
