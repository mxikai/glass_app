-- Reference schema generated from SQLAlchemy models (not used at runtime).

CREATE TABLE students (
    student_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    program TEXT,
    year_level INTEGER,
    role_title TEXT,
    can_approve INTEGER DEFAULT 0,
    status TEXT DEFAULT 'Active'
);

CREATE TABLE budget_plans (
    plan_id INTEGER PRIMARY KEY AUTOINCREMENT,
    academic_year TEXT NOT NULL,
    semester TEXT NOT NULL,
    total_planned_budget REAL NOT NULL,
    member_count INTEGER NOT NULL,
    semestral_fee_amount REAL NOT NULL,
    approval_status TEXT DEFAULT 'Pending',
    approved_date TEXT,
    status TEXT DEFAULT 'Active'
);

CREATE TABLE budget_plan_students (
    plan_id INTEGER NOT NULL,
    student_id TEXT NOT NULL,
    PRIMARY KEY (plan_id, student_id),
    FOREIGN KEY (plan_id) REFERENCES budget_plans(plan_id),
    FOREIGN KEY (student_id) REFERENCES students(student_id)
);

CREATE TABLE fund_buckets (
    bucket_id INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_id INTEGER NOT NULL,
    bucket_name TEXT NOT NULL,
    planned_amount REAL NOT NULL,
    description TEXT,
    FOREIGN KEY (plan_id) REFERENCES budget_plans(plan_id)
);

CREATE TABLE budget_items (
    budget_item_id INTEGER PRIMARY KEY AUTOINCREMENT,
    bucket_id INTEGER NOT NULL,
    item_name TEXT NOT NULL,
    item_type TEXT,
    planned_amount REAL NOT NULL,
    description TEXT,
    FOREIGN KEY (bucket_id) REFERENCES fund_buckets(bucket_id)
);

CREATE TABLE transactions (
    transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_id INTEGER NOT NULL,
    student_id TEXT,
    approver_id TEXT,
    budget_item_id INTEGER,
    amount REAL NOT NULL,
    transaction_type TEXT NOT NULL,
    transaction_status TEXT DEFAULT 'Active',
    approval_status TEXT DEFAULT 'Pending',
    transaction_date TEXT,
    notes TEXT,
    receipt_path TEXT,
    current_hash TEXT,
    previous_hash TEXT,
    FOREIGN KEY (plan_id) REFERENCES budget_plans(plan_id),
    FOREIGN KEY (student_id) REFERENCES students(student_id),
    FOREIGN KEY (approver_id) REFERENCES students(student_id),
    FOREIGN KEY (budget_item_id) REFERENCES budget_items(budget_item_id)
);

CREATE TABLE inventory_items (
    inventory_item_id INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_id INTEGER NOT NULL,
    item_name TEXT NOT NULL,
    quantity INTEGER DEFAULT 1,
    item_condition TEXT,
    status TEXT DEFAULT 'Active',
    date_recorded TEXT,
    FOREIGN KEY (transaction_id) REFERENCES transactions(transaction_id)
);
