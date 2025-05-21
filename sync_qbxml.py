import uuid
from flask import Flask, request, jsonify
import xml.etree.ElementTree as ET
from xml.dom import minidom
import requests

app = Flask(__name__)

# Mock Filevine API base URL
FILEVINE_API = "http://localhost:5000"
FILEVINE_TOKEN = None

# QBWC state
qbwc_session = {"ticket": None, "requests": []}

def get_filevine_token():
    global FILEVINE_TOKEN
    if not FILEVINE_TOKEN:
        response = requests.post(
            f"{FILEVINE_API}/connect/token",
            json={"client_id": "test", "client_secret": "secret"}
        )
        if response.status_code == 200:
            FILEVINE_TOKEN = response.json()["access_token"]
    return FILEVINE_TOKEN

@app.route('/qbwc', methods=['POST'])
def qbwc_endpoint():
    soap_request = request.data.decode('utf-8')
    print("Received QBWC request:", soap_request)

    try:
        root = ET.fromstring(soap_request)
        ns = {
            "soap": "http://schemas.xmlsoap.org/soap/envelope/",
            "qbxml": "http://developer.intuit.com/",
            "ns0": "http://developer.intuit.com/"
        }
        body = root.find("soap:Body", ns)
        for child in body:
            method = child.tag.split('}')[1]
            if method == "serverVersion":
                return soap_response("<serverVersionResult>1.0</serverVersionResult>", method)
            elif method == "clientVersion":
                return soap_response("<clientVersionResult></clientVersionResult>", method)
            elif method == "authenticate":
                username = child.find("ns0:strUserName", ns).text
                password = child.find("ns0:strPassword", ns).text if child.find("ns0:strPassword", ns) is not None else ""
                if username == "sync_user" and password == "":
                    ticket = str(uuid.uuid4())
                    qbwc_session["ticket"] = ticket
                    return soap_response(f"<authenticateResult><string>{ticket}</string><string></string></authenticateResult>", method)
            elif method == "sendRequestXML":
                request_id = len(qbwc_session["requests"])
                qbxml_request = generate_qbxml_request(request_id)
                qbwc_session["requests"].append({"id": request_id, "type": "CustomerQuery" if request_id == 0 else "InvoiceQuery"})
                return soap_response(f"<sendRequestXMLResult>{qbxml_request}</sendRequestXMLResult>", method)
            elif method == "receiveResponseXML":
                response_xml = child.find("ns0:response", ns).text
                process_qbxml_response(response_xml)
                return soap_response("<receiveResponseXMLResult>100</receiveResponseXMLResult>", method)
            elif method == "connectionError":
                return soap_response("<connectionErrorResult>OK</connectionErrorResult>", method)
            elif method == "closeConnection":
                return soap_response("<closeConnectionResult>OK</closeConnectionResult>", method)
            elif method == "getLastError":
                return soap_response("<getLastErrorResult>No Error</getLastErrorResult>", method)
    except Exception as e:
        print(f"Error processing QBWC request: {e}")
        return soap_response("<getLastErrorResult>Server Error</getLastErrorResult>", "getLastError")

    return soap_response("<serverVersionResult>1.0</serverVersionResult>", "serverVersion")

def soap_response(result, method):
    response = f"""
    <?xml version="1.0"?>
    <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
        <soap:Body>
            <{method}Response xmlns="http://developer.intuit.com/">
                {result}
            </{method}Response>
        </soap:Body>
    </soap:Envelope>
    """
    return response, 200, {'Content-Type': 'text/xml'}

def generate_qbxml_request(request_id):
    if request_id == 0:
        return """
        <?xml version="1.0"?>
        <?qbxml version="13.0"?>
        <QBXML>
            <QBXMLMsgsRq onError="stopOnError">
                <CustomerQueryRq requestID="1">
                    <MaxReturned>10</MaxReturned>
                </CustomerQueryRq>
            </QBXMLMsgsRq>
        </QBXML>
        """
    else:
        return """
        <?xml version="1.0"?>
        <?qbxml version="13.0"?>
        <QBXML>
            <QBXMLMsgsRq onError="stopOnError">
                <InvoiceQueryRq requestID="2">
                    <MaxReturned>10</MaxReturned>
                    <IncludeLineItems>true</IncludeLineItems>
                </InvoiceQueryRq>
            </QBXMLMsgsRq>
        </QBXML>
        """

def process_qbxml_response(response_xml):
    try:
        root = ET.fromstring(response_xml)
        ns = {"qbxml": "http://developer.intuit.com/"}
        headers = {"Authorization": f"Bearer {get_filevine_token()}"}

        # Process CustomerQueryRs
        customer_rs = root.find(".//qbxml:CustomerQueryRs", ns)
        if customer_rs is not None:
            for customer_ret in customer_rs.findall("qbxml:CustomerRet", ns):
                list_id = customer_ret.find("qbxml:ListID", ns).text if customer_ret.find("qbxml:ListID", ns) is not None else ""
                full_name = customer_ret.find("qbxml:FullName", ns).text if customer_ret.find("qbxml:FullName", ns) is not None else ""
                email = customer_ret.find("qbxml:Email", ns).text if customer_ret.find("qbxml:Email", ns) is not None else f"{list_id}@example.com"
                payload = {
                    "fullName": full_name,
                    "email": email,
                    "personTypes": ["Client"]
                }
                response = requests.post(f"{FILEVINE_API}/core/contacts", json=payload, headers=headers)
                if response.status_code == 201:
                    print(f"Synced contact {full_name}")
                else:
                    print(f"Failed to sync contact {full_name}: {response.text}")

        # Process InvoiceQueryRs (for expenses)
        invoice_rs = root.find(".//qbxml:InvoiceQueryRs", ns)
        if invoice_rs is not None:
            for invoice_ret in invoice_rs.findall("qbxml:InvoiceRet", ns):
                txn_id = invoice_ret.find("qbxml:TxnID", ns).text if invoice_ret.find("qbxml:TxnID", ns) is not None else ""
                customer_ref = invoice_ret.find("qbxml:CustomerRef/qbxml:ListID", ns).text if invoice_ret.find("qbxml:CustomerRef/qbxml:ListID", ns) is not None else ""
                txn_date = invoice_ret.find("qbxml:TxnDate", ns).text if invoice_ret.find("qbxml:TxnDate", ns) is not None else "2025-05-18"
                for expense_line in invoice_ret.findall("qbxml:ExpenseLineRet", ns):
                    amount = float(expense_line.find("qbxml:Amount", ns).text) if expense_line.find("qbxml:Amount", ns) is not None else 0.0
                    memo = expense_line.find("qbxml:Memo", ns).text if expense_line.find("qbxml:Memo", ns) is not None else ""
                    account_ref = expense_line.find("qbxml:AccountRef/qbxml:FullName", ns).text if expense_line.find("qbxml:AccountRef/qbxml:FullName", ns) is not None else "General Expense"
                    payload = {
                        "projectId": customer_ref,
                        "description": memo,
                        "amount": amount,
                        "date": txn_date,
                        "category": account_ref
                    }
                    response = requests.post(f"{FILEVINE_API}/core/expense", json=payload, headers=headers)
                    if response.status_code == 201:
                        print(f"Synced expense {memo} for invoice {txn_id}")
                    else:
                        print(f"Failed to sync expense {memo}: {response.text}")

    except Exception as e:
        print(f"Error processing QBXML response: {e}")

if __name__ == '__main__':
    app.run(port=5001, debug=True)