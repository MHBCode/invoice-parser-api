from fastapi import FastAPI, HTTPException
import re
from pydantic import BaseModel
from datetime import datetime

app = FastAPI()

class InvoiceRequest(BaseModel):
    text: str

def extract_match(pattern, text):
    """Safely extract a regex match from the text."""
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        if match.groups():
            return match.group(1)  # Use first capturing group if available
        return match.group(0)  # Otherwise, return the full match
    return None

def extract_company_name(text):
    """Extracts a valid company name while ensuring no invoice-related words are captured."""
    company_keywords = r"(Technology|Networks|Consultancy|Solutions|Services|Group|Engineering|Enterprises|Trading|Investments|Corporation|Holding|Club|Hotel|LLC|W\.?L\.?L|L\.?L\.?C)"
    
    # Remove common invoice-related words before extraction
    cleaned_text = re.sub(
        r"\b(INVOICE|TOTAL|BANK DETAILS|ACCOUNT|DESCRIPTION|AMOUNT|SWIFT CODE|IBAN|P\.O\. Box|DATE|CUSTOMER)\b.*", 
        "", text, flags=re.IGNORECASE | re.MULTILINE
    )

    # Extract the first valid company name
    match = re.search(
        rf"([\w\s&\-\(\)]+(?:{company_keywords})\b)", 
        cleaned_text, re.IGNORECASE | re.MULTILINE
    )

    if match:
        company_name = match.group(1).strip()
        if not re.match(r"^\d", company_name) and "bank" not in company_name.lower() and "swift" not in company_name.lower():
            return company_name

    return "Unknown Company"

def extract_total_amount(text):
    """Extracts total invoice amount safely."""
    match = re.search(r"TOTAL\s(?:AMOUNT|QAR|USD|EUR|GBP)?\s*([\d,]+\.\d{2})", text, re.IGNORECASE)
    return float(match.group(1).replace(",", "")) if match else None

def extract_invoice_breakdown(text):
    """Extracts descriptions and prices safely from invoice text."""
    matches = re.findall(r"(Provision.*?|Being Invoice.*?|Services.*?)\s([\d,]+\.\d{2})", text, re.IGNORECASE)
    
    invoice_items = []
    for match in matches:
        try:
            description = match[0].strip()
            price = float(match[1].replace(",", ""))  # Convert price safely
            invoice_items.append({"description": description, "total_price": price})
        except ValueError:
            print(f"⚠️ Failed to convert to float: {match[1]}")  # Debugging log
    
    return invoice_items

def extract_invoice_data(raw_text):
    """Parses invoice text and returns structured data."""
    invoice_data = {
        "seller": {
            "company_name": extract_company_name(raw_text),
            "address": extract_match(r"P\.O\. Box\s\d+", raw_text),
            "contact": {
                "phone": extract_match(r"Phone[:.]?\s(\+\d+)", raw_text),
                "fax": extract_match(r"Fax[:.]?\s(\+\d+)", raw_text),
                "email": extract_match(r"Email[:.]?\s([\w.\-]+@[\w.\-]+)", raw_text),
                "website": extract_match(r"Website[:.]?\s([\w:/.]+)", raw_text)
            }
        },
        "invoice_details": {
            "invoice_date": extract_match(r"DATE[:.]?\s*(\d{1,2}-\w+-\d{4}|\d{2}/\d{2}/\d{4})", raw_text),
            "invoice_no": extract_match(r"INVOICE\s(?:NO|NUMBER)[:.]?\s*([A-Za-z0-9\-]+)", raw_text),
            "currency": extract_match(r"\b(USD|QAR|EUR|GBP|INR)\b", raw_text) or "Unknown Currency"
        },
        "buyer": {
            "company_name": extract_match(r"BUYER[:.]?\s*([\w\s&\-\(\)]+)", raw_text) or "Unknown Buyer",
            "department": "Finance Department",
            "address": extract_match(r"P\.O\. Box\s\d+", raw_text),
            "contact": {
                "phone": "+974 493 2000",
                "fax": "+974 483 1663"
            }
        },
        "invoice_breakdown": extract_invoice_breakdown(raw_text),
        "total_amount": {
            "amount": extract_total_amount(raw_text),
            "currency": extract_match(r"\b(USD|QAR|EUR|GBP|INR)\b", raw_text) or "Unknown Currency",
            "amount_in_words": extract_match(r"Qatari Riyal. (.*?)\.", raw_text)
        },
        "bank_details": {
            "bank_name": extract_match(r"Bank Name[:.]?\s*([\w\s]+)", raw_text),
            "account_no": extract_match(r"Account No[:.]?\s*([\d-]+)", raw_text),
            "iban": extract_match(r"IBAN[:.]?\s*(QA\d{2}[A-Z0-9]{20,30})", raw_text),
            "swift_code": extract_match(r"Swift Code[:.]?\s*([\w\d]+)", raw_text),
            "address": extract_match(r"Address[:.]?\s*(.*?),", raw_text),
            "beneficiary": extract_match(r"Beneficiary[:.]?\s*([\w\s]+)", raw_text)
        },
        "notes": []
    }
    return invoice_data


def extract_invoice_summary(text):
    """Extracts Company Name, Amount, Currency, Date (or today's date if missing), First Line Item, and Invoice Number."""

    company_name = extract_company_name(text)
    
    # Extract Date (First Valid Date Found)
    date_match = re.search(r"(\d{2}[-/]\d{2}[-/]\d{4})|(\d{4}-\d{2}-\d{2})", text)
    invoice_date = date_match.group(0) if date_match else datetime.today().strftime("%Y-%m-%d")  # Use today's date

    # Extract Currency
    currency_match = re.search(r"\b(QAR|USD|EUR|GBP|INR)\b", text, re.IGNORECASE)
    currency = currency_match.group(0) if currency_match else "Unknown Currency"

    # Extract Amount
    amount_match = re.search(r"(\d{1,3}(?:,\d{3})*\.\d{2})\s*(QAR|USD|EUR|GBP|INR)?", text, re.IGNORECASE)
    amount = amount_match.group(1) if amount_match else "Unknown Amount"

    # Extract Invoice Number
    invoice_number_match = re.search(r"(?:Invoice[:\s]?|Invoice No[:\s]?|Invoice Num[:\s]?|INV[:\s]?)\s*([A-Za-z0-9\-]+)", text, re.IGNORECASE)
    invoice_number = invoice_number_match.group(1) if invoice_number_match else "Unknown Invoice Number"

    # Extract **First Line Item Only**
    line_item_match = re.search(r"([\w\s&\-\(\)]+)\s+(\d{1,3}(?:,\d{3})*\.\d{2})", text)
    first_line_item = {
        "description": line_item_match.group(1).strip().replace("\n", " ") if line_item_match else "No Line Item Found",
        "price": line_item_match.group(2).strip() if line_item_match else "0.00"
    } if line_item_match else {}

    return {
        "Company Name": company_name,
        "Invoice Number": invoice_number,
        "Amount": amount,
        "Currency": currency,
        "Date": invoice_date,  # Returns current date if missing
        "First Line Item": first_line_item
    }

@app.get("/")
def home():
    return {"message": "Invoice Parsing API is running!"}

@app.post("/parse_invoice/")
async def parse_invoice(data: InvoiceRequest):
    raw_text = data.text
    if not raw_text:
        raise HTTPException(status_code=400, detail="No text provided.")
    structured_data = extract_invoice_data(raw_text)
    return {"structured_invoice": structured_data}

@app.post("/extract_invoice_summary/")
async def extract_invoice_summary_api(data: InvoiceRequest):
    raw_text = data.text
    if not raw_text:
        raise HTTPException(status_code=400, detail="No text provided.")
    summary = extract_invoice_summary(raw_text)
    return summary
