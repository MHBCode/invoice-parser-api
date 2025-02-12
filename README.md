# Invoice Parsing API
This API processes raw invoice text and returns structured JSON.

## Endpoints
- **POST /parse_invoice/** → Send invoice text and receive structured JSON.

## Example Request
```json
{
  "text": "Paste invoice text here..."
}
