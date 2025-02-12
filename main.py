from fastapi import FastAPI, HTTPException
import re

app = FastAPI()

def extract_company_name(text):
    match = re.search(
        r"(شركة\s[^\n]+|THE DIPLOMATIC CLUB|[A-Za-z\s&]+LLC|[A-Za-z\s&]+W.L.L.|[A-Za-z\s&]+Ltd|[A-Za-z\s&]+Co\.?)",
        text, re.IGNORECASE
    )
    return match.group(0) if match else "Unknown Company"

def extract_match(pattern, text):
    match = re.search(pattern, text, re.IGNORECASE)
    return match.group(1) if match else None

def extract_total_amount(text):
    match = re.search(r"TOTAL\sQAR\s([\d,]+.\d{2})", text, re.IGNORECASE)
    return float(match.group(1).replace(",", "")) if match else None

def extract_invoice_breakdown(text):
    matches = re.findall(r"(Provision.*?|Being Invoice.*?|Services.*?)\s([\d,]+.\d{2})", text, re.IGNORECASE)
    return [{"description": match[0].strip(), "total_price": float(match[1].replace(",", ""))} for match in matches]

def extract_invoice_data(raw_text):
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
            "invoice_no": extract_match(r"INVOICE\sNO[:.]?\s*(\d+|\w+)", raw_text),
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
            "iban": extract_match(r"IBAN[:.]?\s*([\w\s\d]+)", raw_text),
            "swift_code": extract_match(r"Swift Code[:.]?\s*([\w\d]+)", raw_text),
            "address": extract_match(r"Address[:.]?\s*(.*?),", raw_text),
            "beneficiary": extract_match(r"Beneficiary[:.]?\s*([\w\s]+)", raw_text)
        },
        "notes": []
    }
    return invoice_data

@app.post("/parse_invoice/")
async def parse_invoice(data: dict):
    raw_text = data.get("text", "")
    if not raw_text:
        raise HTTPException(status_code=400, detail="No text provided.")
    structured_data = extract_invoice_data(raw_text)
    return {"structured_invoice": structured_data}
