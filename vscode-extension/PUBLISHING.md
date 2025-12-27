# Publishing Toasty Analytics to VS Code Marketplace 🚀

## Free Publishing

**YES!** Publishing to the VS Code Marketplace is **completely FREE**. You just need a Microsoft/Azure DevOps account.

---

## Step-by-Step Publishing Guide

### 1. **Prepare Your Extension**

Make sure everything is ready:
- ✅ Extension works correctly
- ✅ README.md is complete
- ✅ package.json has proper metadata
- ✅ Icons/images are included (optional but recommended)

### 2. **Create Publisher Account**

1. Go to [Visual Studio Marketplace](https://marketplace.visualstudio.com/manage)
2. Sign in with your Microsoft account
3. Click **"Create publisher"**
4. Choose a publisher ID (e.g., "lordbeatus" or "toastimer")
5. Fill in display name and description

### 3. **Get Personal Access Token (PAT)**

1. Go to [Azure DevOps](https://dev.azure.com/)
2. Click your profile → **Personal Access Tokens**
3. Click **+ New Token**
4. Settings:
   - Name: "VS Code Marketplace"
   - Organization: All accessible organizations
   - Expiration: Custom (1 year or more)
   - Scopes: **Marketplace** → **Manage**
5. Click **Create** and **COPY THE TOKEN** (you won't see it again!)

### 4. **Install vsce (Publishing Tool)**

```bash
npm install -g @vscode/vsce
```

### 5. **Login to vsce**

```bash
vsce login <your-publisher-id>
# Paste your PAT when prompted
```

### 6. **Update package.json**

Add these fields to your `package.json`:

```json
{
  "publisher": "your-publisher-id",
  "repository": {
    "type": "git",
    "url": "https://github.com/Lordbeatus/Toastimer.git"
  },
  "icon": "icon.png",
  "galleryBanner": {
    "color": "#FF6B35",
    "theme": "dark"
  },
  "keywords": [
    "code quality",
    "ai",
    "linting",
    "grading",
    "analytics"
  ]
}
```

### 7. **Add Icon (Recommended)**

Create a 128x128 PNG icon named `icon.png` in your extension root.

### 8. **Package Extension**

```bash
cd vscode-extension
vsce package
```

This creates a `.vsix` file.

### 9. **Publish to Marketplace**

```bash
vsce publish
```

Or publish manually:
1. Go to [marketplace.visualstudio.com/manage](https://marketplace.visualstudio.com/manage)
2. Click your publisher
3. Click **+ New Extension** → **Visual Studio Code**
4. Upload your `.vsix` file

---

## 🎯 **After Publishing**

- Extension appears in VS Code Marketplace within **5-10 minutes**
- Users can install via: Extensions → Search "Toasty Analytics"
- Updates: Just run `vsce publish` again (auto-increments version)

---

## 📝 **Before Publishing Checklist**

- [ ] Extension name is unique (search marketplace first)
- [ ] README.md has screenshots/GIFs
- [ ] License file included (MIT recommended)
- [ ] Version follows semver (0.0.1, 0.1.0, 1.0.0, etc.)
- [ ] All commands work correctly
- [ ] Icon added (128x128 PNG)
- [ ] Keywords added for discoverability

---

## 🔄 **Updating Published Extension**

```bash
# Update version in package.json (or use vsce)
vsce publish patch  # 0.0.1 → 0.0.2
vsce publish minor  # 0.0.2 → 0.1.0
vsce publish major  # 0.1.0 → 1.0.0
```

---

## 💰 **Cost**

- **$0** - Publishing is FREE
- **$0** - Hosting is FREE
- **$0** - Updates are FREE

No credit card required! 🎉

---

## 📚 **Resources**

- [Official Publishing Guide](https://code.visualstudio.com/api/working-with-extensions/publishing-extension)
- [Marketplace Management Portal](https://marketplace.visualstudio.com/manage)
- [Extension Manifest Reference](https://code.visualstudio.com/api/references/extension-manifest)

---

**Questions?** Check the SETUP.md or official VS Code docs!
