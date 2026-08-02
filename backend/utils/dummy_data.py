DUMMY_DOCUMENT_TEXT = """INVOICE

Acme Industrial Supply Co.
1400 Commerce Park Drive, Bldg C
Springfield, OH 45503

Invoice No. 84213-B          Date Issued: March 14, 2026          Due Date: April 13, 2026

Bill To: Meridian Manufacturing LLC
1200 Foundry Way, Suite 400
Detroit, MI 48226

Description                              Qty     Unit Price      Amount
--------------------------------------------------------------------------
Industrial Bearings (Model 220-X)         150      $42.50       $6,375.00
Hydraulic Seals (Set of 12)                36      $18.75         $675.00
Lubricant, Synthetic (55-gal drum)          4     $310.00       $1,240.00
Freight & Handling                          1      $95.00          $95.00
--------------------------------------------------------------------------
Subtotal:                                                       $8,385.00
Sales Tax (7.25%):                                                $607.91
Early Payment Discount (2% if paid within 10 days):              -$167.70
--------------------------------------------------------------------------
Total Due:                                                       $8,825.21

Payment Terms: Net 30 days from invoice date. A late fee of 1.5% per month
will be applied to balances outstanding beyond the due date. This agreement
is valid for a 12-month term beginning January 1, 2026 and renews
automatically unless cancelled with 60 days written notice.

Prior Year Comparison: Total spend in fiscal year 2025 was $94,210.00,
representing a 6.3% increase over 2024. Average order processing time
improved to 3.2 business days, down from 4.8 business days.

Remit payment to Acme Industrial Supply Co., Account #77-441982,
routing 021000089. Questions regarding this invoice should be directed
within 15 business days of receipt.
"""

DUMMY_ENTITIES = [
    {"value": "84213-B", "type": "other_number", "label": "Invoice #"},
    {"value": "March 14, 2026", "type": "date", "label": "Date Issued"},
    {"value": "April 13, 2026", "type": "date", "label": "Due Date"},
    {"value": "150", "type": "other_number", "label": "Quantity"},
    {"value": "$42.50", "type": "monetary", "label": "Unit Price"},
    {"value": "$6,375.00", "type": "monetary", "label": "Line Amount"},
    {"value": "36", "type": "other_number", "label": "Quantity"},
    {"value": "$18.75", "type": "monetary", "label": "Unit Price"},
    {"value": "$675.00", "type": "monetary", "label": "Line Amount"},
    {"value": "$310.00", "type": "monetary", "label": "Unit Price"},
    {"value": "$1,240.00", "type": "monetary", "label": "Line Amount"},
    {"value": "$95.00", "type": "monetary", "label": "Unit Price"},
    {"value": "$95.00", "type": "monetary", "label": "Line Amount"},
    {"value": "$8,385.00", "type": "monetary", "label": "Subtotal"},
    {"value": "7.25%", "type": "percentage", "label": "Sales Tax Rate"},
    {"value": "$607.91", "type": "monetary", "label": "Tax Amount"},
    {"value": "2%", "type": "percentage", "label": "Early Payment Discount Rate"},
    {"value": "-$167.70", "type": "monetary", "label": "Discount Amount"},
    {"value": "$8,825.21", "type": "monetary", "label": "Total Due"},
    {"value": "Net 30 days", "type": "duration", "label": "Payment Term"},
    {"value": "1.5%", "type": "percentage", "label": "Late Fee Rate"},
    {"value": "12-month term", "type": "duration", "label": "Agreement Term"},
    {"value": "January 1, 2026", "type": "date", "label": "Term Start Date"},
    {"value": "60 days", "type": "duration", "label": "Notice Period"},
    {"value": "$94,210.00", "type": "monetary", "label": "FY2025 Spend"},
    {"value": "6.3%", "type": "percentage", "label": "YoY Increase"},
    {"value": "3.2 business days", "type": "duration", "label": "Avg Processing Time"},
    {
        "value": "4.8 business days",
        "type": "duration",
        "label": "Prior Avg Processing Time",
    },
    {"value": "77-441982", "type": "other_number", "label": "Account #"},
    {"value": "021000089", "type": "other_number", "label": "Routing #"},
    {"value": "15 business days", "type": "duration", "label": "Response Window"},
]
