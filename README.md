# GLASS: Student Organization Budget Manager

## Overview
GLASS is an offline desktop application designed to help student organizations manage their semestral budgets with structure, clarity, and accountability. Moving beyond fragile spreadsheets, GLASS enforces strict financial hierarchies, ensuring every peso spent is tied to an approved plan.

## Core Features
* **Dynamic Budget Planning:** Create semestral plans that automatically calculate required student fees based on the total planned budget and the active student roster.
* **Strict Fund Hierarchy:** Budgets are divided into specific "Fund Buckets" (e.g., Operations, Events), which contain granular "Budget Items." Expenses cannot be made unless they are tied to an approved Budget Item.
* **Transaction Ledger:** Tracks two types of transactions: 
  * `PAYMENTS`: Semestral fee collections from students.
  * `EXPENSES`: Organizational spending, complete with itemized receipts and approval tracking.
* **Asset & Inventory Tracking:** Automatically bridges physical item purchases from the Expense ledger into a persistent Inventory tracker, alongside legacy inherited items.
* **Exportable Reporting:** Generates official PDF summaries for transparency and liquidation.

## Tech Stack
* **Frontend:** Python, PyQt6 (Modern CSS-styled widgets)
* **Backend:** Python
* **Database:** SQLite (Relational SQL Schema)
