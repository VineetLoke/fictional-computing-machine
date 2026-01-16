const sqlite3 = require('sqlite3').verbose();
const path = require('path');

const dbPath = path.resolve(__dirname, 'corp.db');

const db = new sqlite3.Database(dbPath, (err) => {
    if (err) {
        console.error('Could not connect to database', err);
    } else {
        console.log('Connected to SQLite database');
    }
});

db.serialize(() => {
    db.run(`CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        password TEXT,
        role TEXT
    )`);

    // Seed Data
    db.get("SELECT count(*) as count FROM users", (err, row) => {
        if (row.count === 0) {
            console.log("Seeding database...");
            const stmt = db.prepare("INSERT INTO users (username, password, role) VALUES (?, ?, ?)");
            stmt.run("admin", "supersecret123", "admin");
            stmt.run("user", "user123", "user");
            stmt.finalize();
        }
    });
});

module.exports = db;
