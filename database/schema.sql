-- Пользователи
CREATE TABLE users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
)

-- Активы (счета/вклады)
CREATE TABLE assets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    name TEXT,
    type TEXT,  -- 'deposit' или 'cash'
    currency TEXT DEFAULT 'RUB',
    start_amount REAL,
    start_date DATE,
    interest_rate REAL,  -- NULL для кэша
    current_amount REAL, -- Актуальная сумма с процентами
    last_updated DATE,
    FOREIGN KEY(user_id) REFERENCES users(user_id)
)

-- Операции (пополнения/снятия)
CREATE TABLE transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_id INTEGER,
    type TEXT,  -- 'add' или 'take'
    amount REAL,
    date DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(asset_id) REFERENCES assets(id)
)

напиши sqlite для этого