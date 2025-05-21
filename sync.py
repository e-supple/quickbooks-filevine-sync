import os
import uuid
import json
import time
import schedule
import requests
import glob
from conductor import Conductor
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Conductor
conductor = Conductor(api_key=os.environ.get("CONDUCTOR_SECRET_KEY"))

# Mock Filevine API base URL
FILEVINE_API = "http://localhost:5000"

# EndUser ID for pisanchyn-law-firm
END_USER_ID = "end_usr_Wb4uG5P0SbiOmD"

# Config: Sync ItemLine entries as expenses?
SYNC_ITEM_LINES = False  # Set to True for ItemLine (e.g., Painting), False for ExpenseLine

# In-memory database for QBD-to-Filevine ID mappings
qbd_to_filevine = {
    "customers": {},  # QBD id -> Filevine personId
    "accounts": {},   # QBD id -> Filevine category
    "expenses": {}    # QBD id:LineID -> Filevine BillingItemId
}

# Load existing mappings from the latest mappings_*.json
def load_mappings():
    mapping_files = glob.glob("mappings_*.json")
    if mapping_files:
        latest_file = max(mapping_files, key=os.path.getctime)
        try:
            with open(latest_file, "r") as f:
                global qbd_to_filevine
                qbd_to_filevine.update(json.load(f))
            print(f"Loaded mappings from {latest_file}")
        except Exception as e:
            print(f"Failed to load mappings from {latest_file}: {e}")

# Get Filevine token (mock)
def get_filevine_token():
    try:
        response = requests.post(
            f"{FILEVINE_API}/connect/token",
            json={"client_id": "test", "client_secret": "secret"}
        )
        response.raise_for_status()
        return response.json()["access_token"]
    except Exception as e:
        print(f"Failed to get Filevine token: {e}")
        raise

FILEVINE_TOKEN = get_filevine_token()

def check_customer_exists(qbd_id, full_name, headers):
    try:
        response = requests.get(f"{FILEVINE_API}/core/contacts", headers=headers)
        response.raise_for_status()
        contacts = response.json().get("data", [])
        for contact in contacts:
            if contact.get("fullName") == full_name and qbd_to_filevine["customers"].get(qbd_id) == contact.get("personId"):
                return contact["personId"]
        return None
    except Exception as e:
        print(f"Failed to check customer exists for {full_name}: {e}")
        return None

def check_expense_exists(expense_key, headers):
    try:
        response = requests.get(f"{FILEVINE_API}/core/expense", headers=headers)
        response.raise_for_status()
        expenses = response.json().get("data", [])
        for expense in expenses:
            if qbd_to_filevine["expenses"].get(expense_key) == expense.get("expenseId"):
                return expense["expenseId"]
        return None
    except Exception as e:
        print(f"Failed to check expense exists for {expense_key}: {e}")
        return None

def sync_customers():
    try:
        page = conductor.qbd.customers.list(conductor_end_user_id=END_USER_ID)
        print(f"Fetched {len(page.data)} customers from QuickBooks: {[c.full_name for c in page.data]}")
        if page.data:
            print("First customer attributes:", vars(page.data[0]))
    except Exception as e:
        print(f"Failed to fetch customers: {e}")
        return
    headers = {"Authorization": f"Bearer {FILEVINE_TOKEN}"}
    
    for customer in page.data:
        customer_id = getattr(customer, 'id', None)
        if not customer_id:
            print(f"Skipping customer {customer.full_name}: No id found")
            continue
        if customer_id in qbd_to_filevine["customers"]:
            print(f"Customer {customer.full_name} already synced (in-memory)")
            continue
        existing_person_id = check_customer_exists(customer_id, customer.full_name, headers)
        if existing_person_id:
            print(f"Customer {customer.full_name} already exists on server (Filevine: {existing_person_id})")
            qbd_to_filevine["customers"][customer_id] = existing_person_id
            continue
        payload = {
            "fullName": customer.full_name,
            "email": getattr(customer, 'email', f"{customer_id}@example.com"),
            "personTypes": ["Client"]
        }
        try:
            response = requests.post(f"{FILEVINE_API}/core/contacts", json=payload, headers=headers)
            response.raise_for_status()
            filevine_id = response.json()["personId"]
            qbd_to_filevine["customers"][customer_id] = filevine_id
            print(f"Synced customer {customer.full_name} (QBD: {customer_id}, Filevine: {filevine_id})")
        except Exception as e:
            print(f"Failed to sync customer {customer.full_name}: {e}")

def sync_expenses():
    try:
        account_page = conductor.qbd.accounts.list(conductor_end_user_id=END_USER_ID)
        expense_accounts = [a for a in account_page.data if getattr(a, 'account_type', '').lower() == 'expense']
        print(f"Fetched {len(expense_accounts)} expense accounts from QuickBooks: {[a.full_name for a in expense_accounts]}")
        if expense_accounts:
            print("First expense account attributes:", vars(expense_accounts[0]))
    except Exception as e:
        print(f"Failed to fetch accounts: {e}")
        return
    headers = {"Authorization": f"Bearer {FILEVINE_TOKEN}"}
    
    for account in expense_accounts:
        account_id = getattr(account, 'id', None)
        if not account_id:
            print(f"Skipping account {account.full_name}: No id found")
            continue
        if account_id not in qbd_to_filevine["accounts"]:
            qbd_to_filevine["accounts"][account_id] = account.full_name
            print(f"Mapped account {account.full_name} (QBD: {account_id})")
    
    try:
        invoice_page = conductor.qbd.invoices.list(conductor_end_user_id=END_USER_ID)
        print(f"Fetched {len(invoice_page.data)} invoices from QuickBooks")
    except Exception as e:
        print(f"Failed to fetch invoices: {e}")
        return
    for invoice in invoice_page.data:
        for line in invoice.lines:
            if ((SYNC_ITEM_LINES and hasattr(line, 'item') and line.item and getattr(line.item, 'full_name', '') != 'Subtotal') or
                (not SYNC_ITEM_LINES and hasattr(line, 'account_ref') and line.account_ref)):
                if getattr(line, 'amount', None) in (None, '0.00'):
                    continue
                line_id = getattr(line, 'id', str(uuid.uuid4()))
                expense_key = f"{invoice.id}:{line_id}"
                if expense_key in qbd_to_filevine["expenses"]:
                    print(f"Expense {line.description} already synced (in-memory)")
                    continue
                existing_expense_id = check_expense_exists(expense_key, headers)
                if existing_expense_id:
                    print(f"Expense {line.description} already exists on server (Filevine: {existing_expense_id})")
                    qbd_to_filevine["expenses"][expense_key] = existing_expense_id
                    continue
                account_ref = getattr(line, 'account_ref', None)
                account_id = account_ref.id if account_ref and hasattr(account_ref, 'id') else None
                account_name = qbd_to_filevine["accounts"].get(account_id, "General Expense") if account_id else None
                item_ref = getattr(line, 'item', None)
                item_name = getattr(item_ref, 'full_name', "General Item") if item_ref else "General Item"
                category = account_name if account_name else item_name
                customer_ref = getattr(invoice, 'customer', None)
                project_id = customer_ref.id if customer_ref and hasattr(customer_ref, 'id') else "Unknown"
                payload = {
                    "projectId": project_id,
                    "description": getattr(line, 'description', "No description"),
                    "amount": float(getattr(line, 'amount', 0)),
                    "date": getattr(invoice, 'transaction_date', time.strftime('%Y-%m-%d')),
                    "category": category
                }
                try:
                    response = requests.post(f"{FILEVINE_API}/core/expense", json=payload, headers=headers)
                    response.raise_for_status()
                    filevine_id = response.json()["expenseId"]
                    qbd_to_filevine["expenses"][expense_key] = filevine_id
                    print(f"Synced expense {payload['description']} (QBD: {expense_key}, Filevine: {filevine_id})")
                    sync_billing_item(filevine_id, expense_key, True, headers)
                except Exception as e:
                    print(f"Failed to sync expense {payload['description']}: {e}")
                    sync_billing_item(filevine_id, expense_key, False, headers, str(e))

def sync_billing_item(billing_item_id, system_id, success, headers, note=None):
    payload = [
        {
            "BillingItemId": billing_item_id,
            "SyncSuccessful": success,
            "SystemId": system_id,
            "Note": note or ("Synced successfully" if success else "Sync failed")
        }
    ]
    try:
        response = requests.put(f"{FILEVINE_API}/fv-app/v2/AccountingSync", json=payload, headers=headers)
        response.raise_for_status()
        print(f"Updated sync status for BillingItemId {billing_item_id}: {response.json()}")
    except Exception as e:
        print(f"Failed to update sync status for BillingItemId {billing_item_id}: {e}")

def sync():
    try:
        print(f"Starting sync at {time.strftime('%Y-%m-%d %H:%M:%S')}")
        load_mappings()
        sync_customers()
        sync_expenses()
        print("Sync completed.")
        with open(f"mappings_{uuid.uuid4()}.json", "w") as f:
            json.dump(qbd_to_filevine, f, indent=2)
    except Exception as e:
        print(f"Sync failed: {e}")

def main():
    sync()
    # schedule.every(1).hours.do(sync)
    # while True:
    #     schedule.run_pending()
    #     time.sleep(60)

if __name__ == "__main__":
    main()