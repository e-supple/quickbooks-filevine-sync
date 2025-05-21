import uuid
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from datetime import datetime
from contextlib import asynccontextmanager
import json
from pathlib import Path
from typing import Optional, List

# Global data stores
contacts = []
expenses = []
invoices = []
time_entries = []
sync_status = []

# Persistent storage
base_dir = Path(__file__).resolve().parent  
cache_dir = base_dir / "cache"
cache_dir.mkdir(exist_ok=True)
CONTACTS_FILE = cache_dir / "contacts.json"
EXPENSES_FILE = cache_dir / "expenses.json"
INVOICES_FILE = cache_dir / "invoices.json"
TIME_ENTRIES_FILE = cache_dir / "time_entries.json"
SYNC_STATUS_FILE = cache_dir / "sync_status.json"

# Pydantic models
class TokenRequest(BaseModel):
    client_id: str
    client_secret: str

class TokenResponse(BaseModel):
    access_token: str
    expires_in: int

class Contact(BaseModel):
    personId: str
    fullName: str
    email: Optional[str] = None
    personTypes: Optional[List[str]] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    
class ContactUpdate(BaseModel):
    fullName: Optional[str] = None
    email: Optional[str] = None
    personTypes: Optional[List[str]] = None

class Expense(BaseModel):
    expenseId: str
    projectId: Optional[str] = None
    description: Optional[str] = None
    amount: Optional[float] = None
    date: Optional[str] = None
    category: Optional[str] = None
    created_at: str
    updated_at: str

class ExpenseCreate(BaseModel):
    projectId: Optional[str] = None
    description: Optional[str] = None
    amount: Optional[float] = None
    date: Optional[str] = None
    category: Optional[str] = None

class ExpenseUpdate(BaseModel):
    description: Optional[str] = None
    amount: Optional[float] = None
    date: Optional[str] = None
    category: Optional[str] = None

class Invoice(BaseModel):
    invoiceId: str
    created_at: str

class TimeEntry(BaseModel):
    entryId: str
    created_at: str

class SyncStatus(BaseModel):
    status: str
    last_sync: str

# File I/O
def load_data(file: Path) -> List:
    print(f"Loading file: {file.resolve()}")
    if file.exists():
        try:
            with open(file, "r", encoding="utf-8") as f:
                data = json.load(f)
                print(f"Loaded data: {data}")
                return data
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}")
            return []
    print(f"File not found: {file}")
    return []

def save_data(file: Path, data: List):
    print(f"Saving to file: {file.resolve()}")
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

# Lifespan handler
@asynccontextmanager
async def lifespan(app: FastAPI):
    global contacts, expenses, invoices, time_entries, sync_status
    contacts = load_data(CONTACTS_FILE)
    expenses = load_data(EXPENSES_FILE)
    invoices = load_data(INVOICES_FILE)
    time_entries = load_data(TIME_ENTRIES_FILE)
    sync_status = load_data(SYNC_STATUS_FILE)
    print("Loaded cached data on startup")
    yield
    print("Shutdown complete")

app = FastAPI(
    title="Mock Filevine API",
    description="Mock API for QuickBooks-Filevine integration",
    lifespan=lifespan
)

# Token endpoint
@app.post("/connect/token", response_model=TokenResponse)
async def token(data: TokenRequest):
    if data.client_id == "test" and data.client_secret == "secret":
        return {"access_token": "mock_token", "expires_in": 3600}
    raise HTTPException(status_code=401, detail="Invalid credentials")

# Root endpoint
@app.get("/")
async def index():
    return {
        "message": "Mock Filevine API",
        "endpoints": {
            "/core/contacts": "Manage contacts (GET, POST, PATCH)",
            "/core/expense": "Manage expenses (GET, POST, PATCH, DELETE)",
            "/core/invoice": "Manage invoices (GET, POST)",
            "/core/time": "Manage time entries (GET, POST)",
            "/connect/token": "Mock authentication (POST)",
            "/fv-app/v2/AccountingSync": "Sync billing items (PUT)"
        }
    }

# Contacts endpoints
@app.get("/core/contacts", response_model=List[Contact])
async def get_contacts(personId: Optional[str] = Query(None)):
    contacts = load_data(CONTACTS_FILE)
    if personId:
        for contact in contacts:
            if contact["personId"] == personId:
                return [contact]
        raise HTTPException(status_code=404, detail="Contact not found")
    return contacts

@app.post("/core/contacts", response_model=dict)
async def create_contact(data: Contact):
    contacts = load_data(CONTACTS_FILE)
    person_id = data.personId or str(uuid.uuid4())
    contact = {
        "personId": person_id,
        "fullName": data.fullName,
        "email": data.email,
        "personTypes": data.personTypes,
        "created_at": data.created_at or datetime.utcnow().isoformat(),
        "updated_at": data.updated_at or datetime.utcnow().isoformat()
    }
    contacts.append(contact)
    save_data(CONTACTS_FILE, contacts)
    return {"personId": person_id}

@app.patch("/core/contacts/{person_id}", response_model=dict)
async def update_contact(person_id: str, data: ContactUpdate):
    contacts = load_data(CONTACTS_FILE)
    for contact in contacts:
        if contact["personId"] == person_id:
            if data.fullName:
                contact["fullName"] = data.fullName
            if data.email:
                contact["email"] = data.email
            if data.personTypes:
                contact["personTypes"] = data.personTypes
            contact["updated_at"] = datetime.utcnow().isoformat()
            save_data(CONTACTS_FILE, contacts)
            return {"personId": person_id}
    raise HTTPException(status_code=404, detail="Contact not found")

# Expense endpoints
@app.get("/core/expense", response_model=List[Expense])
async def get_expenses(expenseId: Optional[str] = Query(None)):
    expenses = load_data(EXPENSES_FILE)
    if expenseId:
        for expense in expenses:
            if expense["expenseId"] == expenseId:
                return [expense]
        raise HTTPException(status_code=404, detail="Expense not found")
    return expenses

@app.post("/core/expense", response_model=dict)
async def create_expense(data: ExpenseCreate):
    expenses = load_data(EXPENSES_FILE)
    expense_id = str(uuid.uuid4())
    expense = {
        "expenseId": expense_id,
        "projectId": data.projectId,
        "description": data.description,
        "amount": data.amount,
        "date": data.date,
        "category": data.category,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat()
    }
    expenses.append(expense)
    save_data(EXPENSES_FILE, expenses)
    return {"status": "success", "expenseId": expense_id}

@app.patch("/core/expense", response_model=dict)
async def update_expense(expenseId: str = Query(...), data: ExpenseUpdate = None):
    expenses = load_data(EXPENSES_FILE)
    for expense in expenses:
        if expense["expenseId"] == expenseId:
            if data:
                expense["description"] = data.description if data.description is not None else expense["description"]
                expense["amount"] = data.amount if data.amount is not None else expense["amount"]
                expense["date"] = data.date if data.date is not None else expense["date"]
                expense["category"] = data.category if data.category is not None else expense["category"]
            expense["updated_at"] = datetime.utcnow().isoformat()
            save_data(EXPENSES_FILE, expenses)
            return {"expenseId": expenseId}
    raise HTTPException(status_code=404, detail="Expense not found")

@app.delete("/core/expense", response_model=dict)
async def delete_expense(expenseId: str = Query(...)):
    expenses = load_data(EXPENSES_FILE)
    for i, expense in enumerate(expenses):
        if expense["expenseId"] == expenseId:
            expenses.pop(i)
            save_data(EXPENSES_FILE, expenses)
            return {"status": "success"}
    raise HTTPException(status_code=404, detail="Expense not found")

# Invoice endpoints (placeholder)
@app.get("/core/invoice", response_model=List[Invoice])
async def get_invoices():
    invoices = load_data(INVOICES_FILE)
    return invoices

@app.post("/core/invoice", response_model=dict)
async def create_invoice(data: Invoice):
    invoices = load_data(INVOICES_FILE)
    invoice_id = str(uuid.uuid4())
    invoice = {
        "invoiceId": invoice_id,
        "created_at": datetime.utcnow().isoformat()
    }
    invoices.append(invoice)
    save_data(INVOICES_FILE, invoices)
    return {"invoiceId": invoice_id}

# Time entry endpoints (placeholder)
@app.get("/core/time", response_model=List[TimeEntry])
async def get_time_entries():
    time_entries = load_data(TIME_ENTRIES_FILE)
    return time_entries

@app.post("/core/time", response_model=dict)
async def create_time_entry(data: TimeEntry):
    time_entries = load_data(TIME_ENTRIES_FILE)
    entry_id = str(uuid.uuid4())
    entry = {
        "entryId": entry_id,
        "created_at": datetime.utcnow().isoformat()
    }
    time_entries.append(entry)
    save_data(TIME_ENTRIES_FILE, time_entries)
    return {"entryId": entry_id}

# Accounting sync endpoint (placeholder)
@app.put("/fv-app/v2/AccountingSync", response_model=dict)
async def accounting_sync(data: SyncStatus):
    sync_status = load_data(SYNC_STATUS_FILE)
    sync_status.append({
        "status": data.status,
        "last_sync": data.last_sync
    })
    save_data(SYNC_STATUS_FILE, sync_status)
    return {"status": "success"}