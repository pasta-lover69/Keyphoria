# 🚀 Publishing to the Chrome Web Store

Step-by-step guide to publishing your Secure Password Manager extension.

---

## Prerequisites

Before publishing, you need:

1. **A hosted backend** — Deploy your Flask API so it's publicly accessible:
   - **Vercel** (already configured): `vercel deploy --prod`
   - Note your deployed URL (e.g., `https://password-manager-xyz.vercel.app`)

2. **Extension icons** — Place PNG icons in `browser-extension/icons/`:
   - `icon16.png` (16×16 px)
   - `icon48.png` (48×48 px)
   - `icon128.png` (128×128 px)

3. **A Chrome Developer Account** — $5 one-time fee at:
   https://chrome.google.com/webstore/devconsole

---

## Step 1: Configure for Production

Update `browser-extension/config.json`:
```json
{
  "api": {
    "url": "https://your-deployed-api.vercel.app"
  }
}
```

Update `browser-extension/manifest.json` — replace the `host_permissions`:
```json
"host_permissions": [
  "https://your-deployed-api.vercel.app/*"
]
```

Set Vercel environment variables:
```bash
vercel env add SECRET_KEY         # A random secret string
vercel env add ENCRYPTION_KEY     # Run: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
vercel env add DATABASE_URL       # Your PostgreSQL connection string
vercel env add CORS_ORIGINS       # Your extension's chrome-extension://EXTENSION_ID origin
```

---

## Step 2: Package the Extension

Create a ZIP file of the `browser-extension/` folder:

**Windows:**
```powershell
Compress-Archive -Path .\browser-extension\* -DestinationPath .\password-manager-extension.zip
```

**macOS/Linux:**
```bash
cd browser-extension && zip -r ../password-manager-extension.zip . && cd ..
```

> ⚠️ Make sure the ZIP contains the files directly (not inside a subfolder).

---

## Step 3: Submit to Chrome Web Store

1. Go to https://chrome.google.com/webstore/devconsole
2. Click **"New Item"**
3. Upload your `password-manager-extension.zip`
4. Fill in the listing details:

| Field | Value |
|---|---|
| **Name** | Secure Password Manager |
| **Summary** | Store, manage, and auto-fill your passwords securely |
| **Description** | A secure password manager with AES encryption, auto-fill capabilities, and cross-browser support. |
| **Category** | Productivity |
| **Language** | English |
| **Privacy Policy** | Host your `PRIVACY_POLICY.md` on GitHub or your website and paste the URL |

5. Upload promotional images:
   - Small tile: 440×280 px
   - Screenshot(s): 1280×800 px or 640×400 px

6. Click **"Submit for Review"**

---

## Step 4: After Publishing

Once approved (typically 1-3 business days):

1. **Get your Extension ID** from the Chrome Web Store listing URL
2. **Update CORS** — Add your extension's origin to the `CORS_ORIGINS` env var on Vercel:
   ```
   chrome-extension://YOUR_EXTENSION_ID_HERE
   ```
3. **Test the published extension** — Install from the store and verify all features work

---

## Checklist

- [ ] Backend deployed to Vercel (or other host)
- [ ] Extension icons created (16, 48, 128 px)
- [ ] `config.json` API URL updated to production
- [ ] `manifest.json` host_permissions updated  
- [ ] Environment variables set (`SECRET_KEY`, `ENCRYPTION_KEY`, `DATABASE_URL`, `CORS_ORIGINS`)
- [ ] Privacy policy hosted publicly
- [ ] Extension ZIP packaged
- [ ] Chrome Developer Account created ($5)
- [ ] Extension submitted for review
- [ ] Post-approval: Extension ID added to CORS_ORIGINS
