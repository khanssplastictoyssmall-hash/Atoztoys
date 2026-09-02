ATOZ TOYS - FINAL GENERATION EDITION
Flat ZIP: every file is in the root; no nested folder is required.

Render:
1. Upload all files to the GitHub repository root.
2. Create a PostgreSQL database in Render, or use the render.yaml Blueprint.
3. Set DATABASE_URL, SECRET_KEY, ADMIN_USER and ADMIN_PASSWORD.
4. Start command: gunicorn app:app
5. Storefront: /
6. Admin: /admin

The storefront supports arbitrary-depth category trees, search, product detail,
cart, checkout/order creation, responsive layouts, clickable footer/help items,
banners, and a mobile-friendly admin panel. Product/banner images can be entered as image URLs
from the admin panel. Local SVG graphics are included so the site has visuals
even before real product photography is added.

Admin image upload:
- Product, banner and logo image inputs accept local image files and store them as data URLs in PostgreSQL, so no upload folder is required.
- The default local SVG graphics are included in the flat ZIP.

Important:
- A real payment gateway (Razorpay/Stripe/etc.) requires the merchant's live/test credentials and webhook configuration.
- Customer login/authentication is intentionally lightweight in this edition; guest checkout and local profile are included.

Pre-upload checks completed: ZIP root is flat, archive integrity verified, app.py syntax verified, app.js/admin.js syntax verified, and all local HTML asset references were checked.
