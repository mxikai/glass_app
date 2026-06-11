-- Reference schema generated from SQLAlchemy models (not used at runtime).
-- Physical names follow the base data dictionary while app/service payloads
-- continue to use snake_case keys.

CREATE TABLE Student (
    StudentID VARCHAR(32) NOT NULL,
    Name VARCHAR(120) NOT NULL,
    Program VARCHAR(120),
    YearLevel INTEGER,
    RoleTitle VARCHAR(80),
    CanApprove BOOLEAN DEFAULT 0,
    Status VARCHAR(20) DEFAULT 'Active',
    PRIMARY KEY (StudentID)
);

CREATE TABLE BudgetPlan (
    PlanID INTEGER PRIMARY KEY AUTOINCREMENT,
    AcademicYear VARCHAR(20) NOT NULL,
    Semester VARCHAR(20) NOT NULL,
    TotalPlannedBudget NUMERIC(12, 2) NOT NULL,
    MemberCount INTEGER NOT NULL,
    SemestralFeeAmount NUMERIC(12, 2) NOT NULL,
    ApprovalStatus VARCHAR(20) DEFAULT 'Pending',
    ApprovedDate DATE,
    Status VARCHAR(20) DEFAULT 'Active'
);

CREATE TABLE BudgetPlanStudent (
    PlanID INTEGER NOT NULL,
    StudentID VARCHAR(32) NOT NULL,
    DateIncluded DATE NOT NULL DEFAULT CURRENT_DATE,
    FeeStatus VARCHAR(10) NOT NULL DEFAULT 'Pending',
    PRIMARY KEY (PlanID, StudentID),
    FOREIGN KEY (PlanID) REFERENCES BudgetPlan(PlanID),
    FOREIGN KEY (StudentID) REFERENCES Student(StudentID)
);

CREATE TABLE FundBucket (
    BucketID INTEGER PRIMARY KEY AUTOINCREMENT,
    PlanID INTEGER NOT NULL,
    BucketName VARCHAR(120) NOT NULL,
    PlannedAmount NUMERIC(12, 2) NOT NULL,
    Description VARCHAR(255),
    FOREIGN KEY (PlanID) REFERENCES BudgetPlan(PlanID)
);

CREATE TABLE BudgetItem (
    BudgetItemID INTEGER PRIMARY KEY AUTOINCREMENT,
    BucketID INTEGER NOT NULL,
    ItemName VARCHAR(120) NOT NULL,
    ItemType VARCHAR(50),
    PlannedAmount NUMERIC(12, 2) NOT NULL,
    Description VARCHAR(255),
    FOREIGN KEY (BucketID) REFERENCES FundBucket(BucketID)
);

CREATE TABLE TransactionRecord (
    TransactionID INTEGER PRIMARY KEY AUTOINCREMENT,
    PlanID INTEGER NOT NULL,
    StudentID VARCHAR(32),
    BudgetItemID INTEGER,
    ApprovedByStudentID VARCHAR(32),
    Amount NUMERIC(12, 2) NOT NULL,
    TransactionType VARCHAR(20) NOT NULL,
    TransactionStatus VARCHAR(20) DEFAULT 'Active',
    ApprovalStatus VARCHAR(20) DEFAULT 'Pending',
    TransactionDate DATETIME,
    Notes TEXT,
    ReceiptPath VARCHAR(255),
    AmountOverrideReason TEXT,
    CurrentHash VARCHAR(64),
    PreviousHash VARCHAR(64),
    FOREIGN KEY (PlanID) REFERENCES BudgetPlan(PlanID),
    FOREIGN KEY (StudentID) REFERENCES Student(StudentID),
    FOREIGN KEY (BudgetItemID) REFERENCES BudgetItem(BudgetItemID),
    FOREIGN KEY (ApprovedByStudentID) REFERENCES Student(StudentID)
);

CREATE TABLE ExpenseLineItem (
    LineItemID INTEGER PRIMARY KEY AUTOINCREMENT,
    TransactionID INTEGER NOT NULL,
    ItemName VARCHAR(120) NOT NULL,
    Quantity INTEGER NOT NULL DEFAULT 1,
    UnitCost NUMERIC(12, 2) NOT NULL,
    FOREIGN KEY (TransactionID) REFERENCES TransactionRecord(TransactionID)
);

CREATE TABLE InventoryItem (
    InventoryItemID INTEGER PRIMARY KEY AUTOINCREMENT,
    PurchaseTransactionID INTEGER,
    ExpenseLineItemID INTEGER,
    ItemName VARCHAR(120) NOT NULL,
    Quantity INTEGER DEFAULT 1,
    UnitCost NUMERIC(12, 2),
    ItemCondition VARCHAR(50),
    SourceType VARCHAR(20) DEFAULT 'Purchase',
    SourceNote TEXT,
    Status VARCHAR(20) DEFAULT 'Active',
    DateRecorded DATE,
    FOREIGN KEY (PurchaseTransactionID) REFERENCES TransactionRecord(TransactionID),
    FOREIGN KEY (ExpenseLineItemID) REFERENCES ExpenseLineItem(LineItemID)
);
