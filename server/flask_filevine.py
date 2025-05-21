from datetime import datetime
import json
import os
from flask import Flask, request, jsonify
import uuid
from pathlib import Path

app = Flask(__name__)

# Initialize data lists
base_dir = Path(__file__).resolve().parent
cache_dir = base_dir / 'cache'
os.makedirs(cache_dir)

contacts = []
expenses = []
invoices = []
time_entries = []
sync_status = []

# Persistent storage
# Persistent storage
CONTACTS_FILE = cache_dir / "contacts.json"
EXPENSES_FILE = cache_dir / "expenses.json"
INVOICES_FILE = cache_dir / "invoices.json"
TIME_ENTRIES_FILE = cache_dir / "time_entries.json"
SYNC_STATUS_FILE = cache_dir / "sync_status.json"




def load_data(file):
    if os.path.exists(file):
        with open(file, "r") as f:
            return json.load(f)
    return []

def save_data(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=2)

# Load cached data on startup (optional)
def load_cached_data():
    global contacts, expenses, invoices, time_entries, sync_status
    try:
        for name, lst in [
            ("contacts.json", contacts),
            ("expenses.json", expenses),
            ("invoices.json", invoices),
            ("time_entries.json", time_entries),
            ("sync_status.json", sync_status)
        ]:
            file_path = cache_dir / name
            if file_path.exists():
                with open(file_path, "r", encoding="utf-8") as f:
                    lst.extend(json.load(f))
                print(f"Loaded cached data from {file_path}")
    except Exception as e:
        print(f"Failed to load cached data: {e}")

load_cached_data()

# Token endpoint
@app.route("/connect/token", methods=["POST"])
def token():
    data = request.json
    if data.get("client_id") == "test" and data.get("client_secret") == "secret":
        return jsonify({"access_token": "mock_token", "expires_in": 3600})
    return jsonify({"error": "Invalid credentials"}), 401

@app.route('/', methods=['GET'])
def index():
    return jsonify({
        "message": "Mock Filevine API",
        "endpoints": {
            "/core/contacts": "Manage contacts (GET, POST)",
            "/core/expense": "Manage expenses (GET, POST)",
            "/core/invoice": "Manage invoices (GET, POST)",
            "/core/time": "Manage time entries (GET, POST)",
            "/connect/token": "Mock authentication (POST)",
            "/fv-app/v2/AccountingSync": "Sync billing items (PUT)"
        }
    }), 200

# Contacts endpoints
@app.route("/core/contacts", methods=["GET", "POST"])
def handle_contacts():
    contacts = load_data(CONTACTS_FILE)
    if request.method == "GET":
        contact_id = request.args.get("contactId")
        if contact_id:
            for contact in contacts:
                if contact["contactId"] == contact_id:
                    return jsonify(contact)
            return jsonify({"error": "Contact not found"}), 404
        return jsonify(contacts)
    elif request.method == "POST":
        data = request.json
        contact_id = data.get("contactId", str(uuid.uuid4()))
        contact = {
            "contactId": contact_id,
            "full_name": data.get("full_name"),
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        contacts.append(contact)
        save_data(CONTACTS_FILE, contacts)
        return jsonify({"contactId": contact_id}), 201

@app.route("/core/contacts/<contact_id>", methods=["PATCH"])
def update_contact(contact_id):
    data = request.json
    contacts = load_data(CONTACTS_FILE)
    for contact in contacts:
        if contact["contactId"] == contact_id:
            contact["full_name"] = data.get("full_name", contact["full_name"])
            contact["updated_at"] = datetime.utcnow().isoformat()
            save_data(CONTACTS_FILE, contacts)
            return jsonify({"contactId": contact_id})
    return jsonify({"error": "Contact not found"}), 404

# Expense endpoints
@app.route("/core/expense", methods=["GET", "POST", "PATCH", "DELETE"])
def handle_expenses():
    expenses = load_data(EXPENSES_FILE)
    if request.method == "GET":
        expense_id = request.args.get("expenseId")
        if expense_id:
            for expense in expenses:
                if expense["expenseId"] == expense_id:
                    return jsonify(expense)
            return jsonify({"error": "Expense not found"}), 404
        return jsonify(expenses)
    elif request.method == "POST":
        data = request.json
        expense_id = str(uuid.uuid4())
        expense = {
            "expenseId": expense_id,
            "projectId": data.get("projectId"),
            "description": data.get("description"),
            "amount": data.get("amount"),
            "date": data.get("date"),
            "category": data.get("category"),
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        expenses.append(expense)
        save_data(EXPENSES_FILE, expenses)
        return jsonify({"status": "success", "expenseId": expense_id}), 201
    elif request.method == "PATCH":
        expense_id = request.args.get("expenseId")
        if not expense_id:
            return jsonify({"error": "expenseId query parameter required"}), 400
        data = request.json
        for expense in expenses:
            if expense["expenseId"] == expense_id:
                expense["description"] = data.get("description", expense["description"])
                expense["amount"] = data.get("amount", expense["amount"])
                expense["date"] = data.get("date", expense["date"])
                expense["category"] = data.get("category", expense["category"])
                expense["updated_at"] = datetime.utcnow().isoformat()
                save_data(EXPENSES_FILE, expenses)
                return jsonify({"expenseId": expense_id})
        return jsonify({"error": "Expense not found"}), 404
    elif request.method == "DELETE":
        expense_id = request.args.get("expenseId")
        if not expense_id:
            return jsonify({"error": "expenseId query parameter required"}), 400
        for i, expense in enumerate(expenses):
            if expense["expenseId"] == expense_id:
                expenses.pop(i)
                save_data(EXPENSES_FILE, expenses)
                return jsonify({"status": "success"}), 200
        return jsonify({"error": "Expense not found"}), 404
    
if __name__ == '__main__':
    app.run(port=5000, debug=True)