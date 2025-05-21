QuickBooks-Filevine Integration
Overview
This project develops a synchronization solution to integrate QuickBooks Enterprise Desktop (QBD) with Filevine for a law firm, replacing an existing subscription service. The current implementation uses a mock Filevine server (fast_filevine.py) and syncs data with a sample QBD company file for testing. The solution supports bidirectional contact synchronization and unidirectional expense synchronization (QBD to Filevine), with placeholder endpoints for invoices, time entries, and accounting sync.
Current Status

Contacts: Bidirectional sync of 146 customers (e.g., “Abercrombie, Kristy” with QBD ID 150000-933272658 to Filevine ID c04ae665-e218-4d3c-95c9-1a58d51bcbec).
Expenses: Unidirectional sync (QBD to Filevine) implemented but not syncing due to missing ExpenseLine entries (SYNC_ITEM_LINES=False).
Data: 113 invoices, 44 expense accounts mapped, stored in mappings.db and cache/*.json.
Filevine API: Awaiting API keys (expected May 21 or 22, 2025); using mock server (http://localhost:5000).
EndUser ID: end_usr_Wb4uG5P0SbiOmD.

Project Structure
quickbooks-filevine-sync/
├── cache/                  # JSON cache files (contacts.json, expenses.json, etc.)
├── logs/                   # Sync logs (sync.log)
├── server/                 # Mock Filevine server
│   └── fast_filevine.py    # FastAPI-based mock API
├── tests/                  # Test scripts
│   └── test_invoices.py    # Invoice line item tester
├── sync.py                 # Main sync script
├── mappings.db             # SQLite DB for ID mappings
└── README.md               # This file

Features

Bidirectional Contact Sync: Syncs customer names between QBD and Filevine (e.g., updates “Abercrombie, Kristy” to “Abercrombie, Kristen”).
Unidirectional Expense Sync: Syncs QBD expenses (e.g., “Medical records charge 100 pages $125.00”) to Filevine (pending ExpenseLine fix).
Mock Filevine API: Supports /core/contacts, /core/expense (GET, POST, PATCH, DELETE), /core/invoice, /core/time, /fv-app/v2/AccountingSync, and /connect/token.
Persistent Storage: Stores data in cache/*.json and mappings.db.
Logging: Sync operations logged to logs/sync.log.

Requirements

OS: Windows (for QBD compatibility).
Python: 3.8+.
QBD: QuickBooks Enterprise Desktop with Web Connector (QBWC) configured.
Tools:
uv package manager.
Dependencies: fastapi, uvicorn, pydantic, conductor-py, requests, sqlite3.


Sample QBD Company File: Used for testing (e.g., trial version).

Setup

Clone Repository:
git clone <repository-url>
cd S:\Projects\quickbooks-filevine-sync

activate virtual environment
.venv/Scripts/activate


Install Dependencies:
uv sync
uv add fastapi uvicorn pydantic conductor-py requests


Configure QBD:

Install QBD trial version with a sample company file.
Enable QBWC: File > Update Web Services, add application for sync.py.
Set Preferences > General: Check Keep QuickBooks running.


Set Up Mock Server:
cd S:\Projects\quickbooks-filevine-sync\server
mkdir cache
New-Item cache\contacts.json -ItemType File -Value "[]"
New-Item cache\expenses.json -ItemType File -Value "[]"
New-Item cache\invoices.json -ItemType File -Value "[]"
New-Item cache\time_entries.json -ItemType File -Value "[]"
New-Item cache\sync_status.json -ItemType File -Value "[]"


Run Mock Server:
cd server/
uvicorn fast_filevine:app --reload
uv run uvicorn fast_filevine:app --host 0.0.0.0 --port 5000


Run Sync:
cd S:\Projects\quickbooks-filevine-sync
uv run python .\sync.py



Usage

Mock Server Endpoints:

POST /connect/token: Authenticate (use client_id: test, client_secret: secret).curl -X POST http://localhost:5000/connect/token -H "Content-Type: application/json" -d '{"client_id":"test","client_secret":"secret"}'


GET/POST /core/contacts: List or create contacts.curl -X POST http://localhost:5000/core/contacts -H "Authorization: Bearer mock_token" -H "Content-Type: application/json" -d '{"contactId":"c04ae665-e218-4d3c-95c9-1a58d51bcbec","full_name":"Abercrombie, Kristy","created_at":"2025-05-20T08:55:00Z","updated_at":"2025-05-20T08:55:00Z"}'


PATCH /core/contacts/{contact_id}: Update contact.curl -X PATCH http://localhost:5000/core/contacts/c04ae665-e218-4d3c-95c9-1a58d51bcbec -H "Authorization: Bearer mock_token" -H "Content-Type: application/json" -d '{"full_name":"Abercrombie, Kristen"}'


GET/POST/PATCH/DELETE /core/expense: Manage expenses.curl -X POST http://localhost:5000/core/expense -H "Authorization: Bearer mock_token" -H "Content-Type: application/json" -d '{"projectId":"c04ae665-e218-4d3c-95c9-1a58d51bcbec","description":"Medical records charge 100 pages","amount":125.00,"date":"2025-05-20","category":"Professional Fees:Legal Fees"}'




Sync Process:

Run sync.py to sync contacts and expenses.
Check logs/sync.log for status (e.g., “Fetched 146 customers”).
Verify mappings in mappings.db and cache/*.json.


Test Expenses:

Run test_invoices.py to diagnose ExpenseLine issues:cd S:\Projects\quickbooks-filevine-sync\tests
uv run python .\test_invoices.py


Known Issues

Expense Sync: No expenses synced ("expenses": {} in mappings_54df36ec-...json) due to missing ExpenseLine entries. Set SYNC_ITEM_LINES=False and add ExpenseLine in QBD (e.g., for “Medical records charge”).
Filevine API: Awaiting keys; mock server simulates /core/contacts, /core/expense, etc.
Placeholder Endpoints: /core/invoice, /core/time, /fv-app/v2/AccountingSync lack full implementation.

Next Steps

Obtain Filevine API Keys: Expected May 21 or 22, 2025.
Integrate Filevine API:
Update sync.py with https://api.filevine.io and OAuth 2.0.
Map QBD fields to Filevine’s data model.


Fix Expense Sync:
Run test_invoices.py to confirm ExpenseLine.
Update sync.py to sync expenses.


Enhance Endpoints:
Add fields to /core/invoice, /core/time, /fv-app/v2/AccountingSync.


Production Deployment:
Configure Task Scheduler for sync.py and fast_filevine.py.
Test with real QBD data.



Contributing

Report issues or submit pull requests to <repository-url>.
Contact the law firm’s IT team for QBD access or Filevine API details.

License
Proprietary; for internal use by the law firm.


* This was automatically generated after uplioading to the files to Grok and telling it to summarize what each file is doing in a readme.md; I also had Grok take a look for ways to refactor and improve code readabilty 
* The main mock filevine server is the flask_filevine.py server, the fast_filevine.py server was created after and something I am trying to convert the flask original over to. 
