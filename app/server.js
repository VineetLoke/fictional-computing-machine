cd /workspaces/fictional-computing-machine/safe-agent
cp .env.example .envconst express = require('express');
const fs = require('fs');
const path = require('path');
const morgan = require('morgan');
const multer = require('multer');
const db = require('./database');

const app = express();
const PORT = 3000;

// Middleware
app.use(express.urlencoded({ extended: true }));
app.use(express.static('public'));
app.set('view engine', 'ejs');

// Logging
const accessLogStream = fs.createWriteStream(path.join(__dirname, 'access.log'), { flags: 'a' });
app.use(morgan('combined', { stream: accessLogStream }));
app.use(morgan('dev'));

// Vulnerability 3: Insecure File Upload Configuration
const storage = multer.diskStorage({
    destination: (req, file, cb) => {
        // Ensure directory exists
        const uploadDir = path.join(__dirname, 'public/uploads');
        if (!fs.existsSync(uploadDir)) {
            fs.mkdirSync(uploadDir, { recursive: true });
        }
        cb(null, uploadDir);
    },
    filename: (req, file, cb) => {
        // UNSAFE: Keeps original name (e.g., shell.html or malicious.js)
        cb(null, file.originalname);
    }
});
const upload = multer({ storage: storage });

// Routes

app.get('/', (req, res) => {
    res.render('index', { error: null });
});

// VULNERABILITY 1: SQL Injection
app.post('/login', (req, res) => {
    const { username, password } = req.body;

    // UNSAFE: Direct concatenation
    const query = `SELECT * FROM users WHERE username = '${username}' AND password = '${password}'`;

    console.log("Executing SQLi Query:", query);

    db.get(query, (err, row) => {
        if (err) {
            return res.render('index', { error: 'Database error' });
        }
        if (row) {
            res.redirect(`/dashboard?user=${row.username}`);
        } else {
            res.render('index', { error: 'Invalid credentials' });
        }
    });
});

// VULNERABILITY 2: Reflected XSS
app.get('/search', (req, res) => {
    const query = req.query.q || '';
    // We are passing this to search_results.ejs, which renders it with <%- %>
    res.render('search_results', { query, user: 'Guest' });
});

// VULNERABILITY 3: File Upload Processing
app.post('/upload', upload.single('document'), (req, res) => {
    if (!req.file) {
        return res.send('No file uploaded.');
    }
    // File uploaded to public/uploads, directly accessible!
    res.send(`File uploaded! <br> Access it here: <a href="/uploads/${req.file.originalname}" target="_blank">/uploads/${req.file.originalname}</a>`);
});

app.get('/dashboard', (req, res) => {
    const user = req.query.user || 'Guest';
    res.render('dashboard', { user });
});

app.listen(PORT, () => {
    console.log(`Server running at http://localhost:${PORT}`);
});
