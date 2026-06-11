-- Sample seed data for local testing only.

INSERT INTO Student (
    StudentID,
    Name,
    Program,
    YearLevel,
    RoleTitle,
    CanApprove,
    Status
)
VALUES ('2024-0001', 'Alex Rivera', 'BSCS', 2, 'Treasurer', 1, 'Active');

INSERT INTO BudgetPlan (
    AcademicYear,
    Semester,
    TotalPlannedBudget,
    MemberCount,
    SemestralFeeAmount,
    ApprovalStatus,
    Status
)
VALUES ('2025-2026', '1st', 50000.00, 1, 50000.00, 'Approved', 'Active');

INSERT INTO BudgetPlanStudent (
    PlanID,
    StudentID,
    DateIncluded,
    FeeStatus
)
VALUES (1, '2024-0001', date('now'), 'Pending');

INSERT INTO FundBucket (
    PlanID,
    BucketName,
    PlannedAmount,
    Description
)
VALUES (1, 'Operations Fund', 20000.00, 'Org operations');

INSERT INTO BudgetItem (
    BucketID,
    ItemName,
    ItemType,
    PlannedAmount,
    Description
)
VALUES (1, 'Office Supplies', 'Supplies', 5000.00, 'Basic materials');

INSERT INTO TransactionRecord (
    PlanID,
    StudentID,
    ApprovedByStudentID,
    Amount,
    TransactionType,
    TransactionStatus,
    ApprovalStatus,
    TransactionDate,
    Notes
)
VALUES (
    1,
    '2024-0001',
    '2024-0001',
    50000.00,
    'PAYMENT',
    'Active',
    'Approved',
    '2026-05-24T10:00:00',
    'Initial payment'
);
