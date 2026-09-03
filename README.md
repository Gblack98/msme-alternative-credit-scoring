# MSME Alternative Credit Scoring

Scoring API for micro and small businesses that have no bank statement, no tax record
and no credit history, but do leave a mobile money trail.

The score is built from that trail: transaction count and volume over 90 days, number
of counterparties, recency, whether income arrives regularly, plus the age of the
business and the size of the request against monthly revenue.

## Status

The scorecard is currently a set of weighted rules, not a trained model. The features
are already extracted and logged, so the weights can be replaced by a model once there
is enough repayment history to learn from. See the TODO in `app/main.py`.

## API

```bash
curl -X POST http://localhost:8000/score \
  -H "Content-Type: application/json" \
  -d '{
    "business_id": "BIZ-001",
    "country_code": "SN",
    "sector": "retail",
    "years_in_operation": 2.5,
    "monthly_revenue_usd": 800,
    "requested_amount_usd": 1500,
    "loan_purpose": "inventory",
    "mobile_money": {
      "total_transactions_90d": 45,
      "total_volume_usd_90d": 3200,
      "has_regular_income": true
    }
  }'
```

```json
{
  "credit_score": 680,
  "risk_band": "B",
  "decision": "approved",
  "max_loan_amount_usd": 1500,
  "recommended_rate_pct": 12.0,
  "explanation": [
    "high mobile money activity",
    "business established for 2.5 years",
    "regular income pattern detected"
  ]
}
```

Score bands: A above 700, B above 600, C above 500 and sent to review, D declined.

## Stack

FastAPI for the endpoint, Supabase for storage and the audit log. Every score is
written to Supabase in the background, so a decision can be explained after the fact.

## Setup

```bash
pip install -r requirements.txt
export SUPABASE_URL=... SUPABASE_KEY=...
supabase db push
uvicorn app.main:app --reload
```

## Author

Ibrahima Gabar Diop
[GitHub](https://github.com/Gblack98) · [Kaggle](https://www.kaggle.com/ibrahimagabardiop)
