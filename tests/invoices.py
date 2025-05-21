import os
from conductor import Conductor
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Conductor
conductor = Conductor(api_key=os.environ.get("CONDUCTOR_SECRET_KEY"))

# List invoices
try:
    page = conductor.qbd.invoices.list(conductor_end_user_id="end_usr_Wb4uG5P0SbiOmD")
    print(f"Fetched {len(page.data)} invoices from QuickBooks")
    for invoice in page.data:
        print(f"\nInvoice ID: {invoice.id}, Ref Number: {getattr(invoice, 'ref_number', 'Unknown')}, "
              f"Customer: {getattr(invoice.customer, 'full_name', 'Unknown')}, "
              f"Date: {getattr(invoice, 'transaction_date', 'Unknown')}")
        print("Invoice attributes:", vars(invoice))
        for line in invoice.lines:
            line_type = getattr(line, 'object_type', 'Unknown')
            description = getattr(line, 'description', 'No description')
            amount = getattr(line, 'amount', 'None')
            item_name = getattr(line.item, 'full_name', 'None') if hasattr(line, 'item') and line.item else 'None'
            account_name = getattr(line.account_ref, 'full_name', 'None') if hasattr(line, 'account_ref') and line.account_ref else 'None'
            print(f"  Line ID: {line.id}, Type: {line_type}, Description: {description}, "
                  f"Amount: {amount}, Item: {item_name}, Account: {account_name}")
            if "Medical records" in description.lower():
                print(f"  **FOUND Medical records charge**: {description}, Amount: {amount}")
except Exception as e:
    print(f"Failed to fetch invoices: {e}")