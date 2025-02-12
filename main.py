from fastapi import FastAPI, HTTPException
import re

app = FastAPI()

def extract_match(pattern, text):
    """Safely extract a regex match from the text."""
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        if match.groups():
            return match.group(1)  # Use first capturing group if available
        return match.group(0)  # Otherwise, return the full match
    return None


def extract_company_name(text):
    """Extracts a valid company name while removing extra words and \n characters."""

    # Define business-related keywords
    company_keywords = r"(Technology|Networks|Consultancy|Solutions|Services|Group|Engineering|Enterprises|Trading|Investments|Corporation|Holding)"

    # **Step 1: If `\n` exists, start searching after it (but don't keep `\n`)**
    text = re.sub(r"^\s*IN\n", "", text, flags=re.IGNORECASE)  # Removes "IN\n" at the beginning if present

    # **Step 2: Extract the company name using business keywords**
    match = re.search(
        rf"\b([\w\s&\-\(\)]+(?:{company_keywords}|W\.?L\.?L|L\.?L\.?C)\b)", 
        text, re.IGNORECASE | re.MULTILINE
    )

    if match:
        company_name = match.group(1).strip()

        # **Step 3: Remove any remaining `\n` from the extracted name**
        company_name = company_name.replace("\n", " ")

        # **Step 4: Ensure no unwanted extra words are included**
        if "bank" not in company_name.lower() and "swift" not in company_name.lower():
            return company_name

    return "Unknown Company"





def extract_total_amount(text):
    """Extracts total invoice amount safely."""
    match = re.search(r"TOTAL\s(?:AMOUNT|QAR)?\s*([\d,]+\.\d{2})", text, re.IGNORECASE)
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
            "currency": "QAR"
        },
        "buyer": {
            "company_name": "Qatar Financial Market Authority",
            "department": "Finance Department",
            "address": "P.O. Box 25552, Doha, Qatar",
            "contact": {
                "phone": "+974 493 2000",
                "fax": "+974 483 1663"
            }
        },
        "invoice_breakdown": extract_invoice_breakdown(raw_text),
        "total_amount": {
            "amount": extract_total_amount(raw_text),
            "currency": "QAR",
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

@app.get("/")
def home():
    return {"message": "Invoice Parsing API is running!"}

@app.post("/parse_invoice/")
async def parse_invoice(data: dict):
    raw_text = data.get("text", "")
    if not raw_text:
        raise HTTPException(status_code=400, detail="No text provided.")
    structured_data = extract_invoice_data(raw_text)
    return {"structured_invoice": structured_data}
