-- Sample seed data for local testing only.

INSERT INTO students (student_id, name, program, year_level, role_title, can_approve, status)
VALUES ('S-1001', 'Alex Rivera', 'BSCS', 2, 'Treasurer', 1, 'Active');

INSERT INTO budget_plans (academic_year, semester, total_planned_budget, member_count, semestral_fee_amount, approval_status, status)
VALUES ('2025-2026', '1st', 50000.00, 50, 1000.00, 'Approved', 'Active');

INSERT INTO budget_plan_students (plan_id, student_id)
VALUES (1, 'S-1001');

INSERT INTO fund_buckets (plan_id, bucket_name, planned_amount, description)
VALUES (1, 'Operations Fund', 20000.00, 'Org operations');

INSERT INTO budget_items (bucket_id, item_name, item_type, planned_amount, description)
VALUES (1, 'Office Supplies', 'Supplies', 5000.00, 'Basic materials');

INSERT INTO transactions (plan_id, student_id, amount, transaction_type, transaction_status, approval_status, transaction_date, notes)
VALUES (1, 'S-1001', 1000.00, 'PAYMENT', 'Active', 'Approved', '2026-05-24T10:00:00Z', 'Initial payment');
