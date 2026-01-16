# 👻 GhostProtocol: DevSecOps & Ethical Hacking Sandbox

Welcome to your personal hacking lab! This project is a deliberately vulnerable web application designed to teach you the basics of **Application Security** and **DevOps**.

## 🚀 Setup & Installation

1.  **Open Terminal** (Command Prompt or PowerShell).
2.  Navigate to the app directory:
    ```bash
    cd ghost-protocol/app
    ```
3.  Install dependencies (if not already done):
    ```bash
    npm install
    ```
4.  Start the server:
    ```bash
    npm start
    ```
    You should see: `Server running at http://localhost:3000`

---

## 🎯 Mission 1: SQL Injection (Login Bypass)

**Objective**: Log in as `admin` without knowing the password.
**The Vulnerability**: The application directly concatenates your input into the SQL query used to check credentials.

### Steps to Exploit:
1.  Open your browser to `http://localhost:3000`.
2.  In the **Username** field, type:
    ```text
    admin' --
    ```
3.  Type *anything* in the Password field.
4.  Click **Login**.

**Why it works**:
The query becomes:
```sql
SELECT * FROM users WHERE username = 'admin' --' AND password = '...'
```
The `--` comment character tells the database to ignore the rest of the line (the password check!).

### Automated Exploit (Python):
Run the script to see how hackers automate this:
```bash
# In a new terminal
cd ghost-protocol/exploits
python exploit_sqli.py
```

---

## 🎯 Mission 2: Reflected XSS (Client-Side Attack)

**Objective**: Execute arbitrary JavaScript in the victim's browser.
**The Vulnerability**: The "Search" feature repeats your input back to you on the page without escaping HTML tags.

### Steps to Exploit:
1.  Log in (using the SQLi trick above).
2.  Go to the **Dashboard**.
3.  In the "Search Documents" box, type:
    ```html
    <script>alert('HACKED')</script>
    ```
4.  Press Enter.
5.  If you see a pop-up alert box, you have successfully performed a Cross-Site Scripting (XSS) attack!

---

## 🎯 Mission 3: Unrestricted File Upload (Remote Code Execution)

**Objective**: Upload a malicious file (e.g., an HTML file that steals cookies) instead of a document.
**The Vulnerability**: The server blindly trusts whatever file you send it.

### Steps to Exploit:
1.  Create a file named `exploit.html` on your Desktop with this content:
    ```html
    <h1>I control this page now!</h1>
    <script>alert('RCE Successful')</script>
    ```
2.  Go to the **Dashboard**.
3.  Find the "Upload Profile Document" section.
4.  Select your `exploit.html` file.
5.  Click **Upload**.
6.  Click the link provided (e.g., `/uploads/exploit.html`).
7.  Your HTML file is now being served by the corporate server! In a real scenario, this could be a PHP shell to take over the whole machine.

---

## 🛡️ Blue Team: How to Fix It?

Now that you've broken it, try to fix it!
Open `app/server.js` and look for the vulnerability comments.

*   **Fix SQLi**: Use "Parameterized Queries" (Prepared Statements) instead of string concatenation.
*   **Fix XSS**: Use EJS properly (escape output) or sanitize input using a library.
*   **Fix Upload**: Validate the `file.mimetype` and rename the file to a safe UUID.
