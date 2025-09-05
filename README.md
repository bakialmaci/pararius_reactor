
# Pararius Reactor

A Python bot that automatically reacts to [Pararius](https://www.pararius.com) saved-search email alerts.  
It monitors your inbox for Pararius notifications and triggers automated reactions, saving you time when applying for properties.

## 🚀 Features
- Monitors your subscribed/saved Pararius search alerts via email
- Extracts property details from incoming messages
- Opens and reacts to listings automatically with Playwright
- Configurable session storage (no credentials committed)
- Designed with modular components (`MailClient`, `ParariusSession`, `ParariusBot`, `NetworkManager`)

## ⚙️ Installation

- Clone the repository:
```bash
git clone https://github.com/bakialmaci/pararius_reactor.git
```

- Goto project directory
```bash
cd pararius_reactor/
```


- Create a virtual environment and install dependencies:
```bash
python3 -m venv venv
source venv/bin/activate   # on Linux/macOS
venv\Scripts\activate      # on Windows (NOT TESTED)

pip install -r requirements.txt

playwright install
```
## 🔑 Configuration

This project needs two things to run:

1- **Pararius session cookies** (to send reactions)

2-  **Email credentials** (to read Pararius alert emails)



### 1. Session cookies (`session.json`)

We use a `session.json` file to store your Pararius login session.
   - [Chrome: Cookie-Editor](https://chrome.google.com/webstore/detail/cookie-editor/hlkenndednhfkekhgcdicdfddnkalmdm)  
   - [Firefox: Cookie-Editor](https://addons.mozilla.org/en-US/firefox/addon/cookie-editor/)  

```
Steps:
1. Install a cookie export extensions:   

2. Log in to Pararius.

3. Open the extension → `Export` all cookies for `pararius.com`.

4. Save the exported JSON as `session.json` in the project root:
```

### 2. Email credentials (`.env`)

The bot connects to your mailbox (IMAP) to read saved-search alert emails.

We use a `.env` file for configuration. Create a file named `.env` in the project root:

```bash
EMAIL_USER=yourname@gmail.com
EMAIL_PASS=your_app_password
```

### How to get your Gmail App Password:
```bash
1. Go to [Google Account Security](https://myaccount.google.com/security).
2. Enable **2-Step Verification** if not already active.
3. Under **App passwords**, generate a new password:
   - App: "Mail"
   - Device: "Other" → name it "ParariusBot"
4. Copy the 16-character password and paste it into `.env` as `EMAIL_PASS`.
```

- Now the bot ready to read your alert emails via IMAP and use cookies in `session.json` to react on Pararius in ~5 Seconds depending network connection.



#### ⚠️ **Important:**  
- Do not share or commit your `session.json`.  
- It contains authentication cookies tied to your Pararius account.  
- The file is already included in `.gitignore` for safety.
- Do not use your real Gmail password. Always use an App Password.

## How to run bot
```bash
python -m pararius_reactor
python3 pararius_reactor/main.py
```
- And you will see and output something like that;
```bash
2025-09-05T14:02:28.580Z pararius-auto-reactor INFO main Starting pararius-auto-reactor
2025-09-05T14:02:28.580Z pararius-auto-reactor INFO main Owner: Baki Almaci | Date: 2025-09-04
2025-09-05T14:02:28.580Z pararius-auto-reactor INFO NetworkManager [Network] Manager started (interval=1.0s)
2025-09-05T14:02:28.580Z pararius-auto-reactor INFO main Bot instantiated. Entering run_forever(interval=1.00s)…
2025-09-05T14:02:28.580Z pararius-auto-reactor INFO ParariusBot [Bot] Pararius auto-reactor started (interval=1.00s).
```

## Contributing to Pararius Reactor

Thanks for considering contributing! 🎉

## How to Contribute
1- Fork the repository

2- Create a new branch for your feature/fix:
   ```bash
   git checkout -b feature/amazing-feature
   ```