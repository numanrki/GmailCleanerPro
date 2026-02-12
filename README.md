# 📧 Gmail Cleaner Pro

A free, open-source desktop application to clean your Gmail inbox. Select unwanted senders and delete all their emails with one click!

**Author:** [@numanrki](https://github.com/numanrki) | [Twitter/X](https://x.com/numanrki) | [☕ Buy me a coffee](https://buymeacoffee.com/numanrki)

![Gmail Cleaner Pro Screenshot](screenshot.png)

## ✨ Features

- 🔐 **Secure OAuth Login** - Connect with your Gmail safely
- 📊 **Live Email Scanning** - Watch as emails are fetched in real-time
- 🎯 **Bulk Delete** - Select multiple senders and delete all their emails
- 🔍 **Search & Filter** - Quickly find specific senders
- 💾 **No Data Stored** - Your emails stay on Google's servers
- 📦 **Portable EXE** - Just download and run, no installation needed

## 🚀 Quick Start

### Option 1: Download Executable (Windows) ⭐ Recommended
1. Go to [Releases](https://github.com/numanrki/gmail-cleaner-pro/releases)
2. Download `GmailCleanerPro.exe`
3. Double-click to run - that's it!

### Option 2: Run from Source
```bash
# Clone the repository
git clone https://github.com/numanrki/gmail-cleaner-pro.git
cd gmail-cleaner-pro

# Install dependencies
pip install -r requirements.txt

# Run the app
python gmail_cleaner_pro.py
```

## 📋 Requirements

- Python 3.7+
- Windows / macOS / Linux

## 🔒 Privacy & Security

- **Your credentials are NEVER stored** - We use Google's official OAuth 2.0
- **No data collection** - The app runs 100% locally on your computer
- **Open source** - Review the code yourself!
- **Only accesses what's needed** - We only request email management permissions

## 📖 How to Use

1. **Connect Gmail** - Click the button and sign in with Google
2. **Load Senders** - Click to scan your inbox and see all senders
3. **Select Senders** - Click on senders you want to delete (Ctrl+Click for multiple)
4. **Add to Delete List** - Move selected senders to the delete queue
5. **Delete** - Click the big red button to permanently delete all emails

## 🛠️ Building from Source

### Create Executable (Windows)
```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name "Gmail Cleaner Pro" gmail_cleaner_pro.py
```

The executable will be in the `dist` folder.

## ❓ FAQ

**Q: Is this safe to use?**
A: Yes! We use Google's official OAuth 2.0 authentication. Your password is never shared with us.

**Q: Will this delete emails permanently?**
A: Yes, deleted emails are permanently removed and cannot be recovered.

**Q: Can I undo deletions?**
A: No, deletions are permanent. Always double-check before deleting.

**Q: Why does Google show "unverified app" warning?**
A: This is a personal/open-source project. Click "Advanced" → "Go to Gmail Cleaner Pro" to proceed.

## 📄 License

MIT License - Feel free to use, modify, and distribute!

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## ⭐ Star this repo if it helped you!
