# 🌍 MSME Alternative Credit Scoring — Africa

![FastAPI](https://img.shields.io/badge/FastAPI-0.110-009688) ![Supabase](https://img.shields.io/badge/Supabase-PostgreSQL-3ECF8E) ![Africa](https://img.shields.io/badge/Market-Africa-orange) ![Financial Inclusion](https://img.shields.io/badge/SDG-Financial_Inclusion-blue)

> Real-time credit scoring API for micro/small businesses in Africa using **alternative data** (mobile money, behavioral signals) — because **80% of MSMEs are unbanked** and excluded from traditional credit.

## Problem

Traditional credit scoring requires: bank statements, tax records, collateral, credit history.  
In Sub-Saharan Africa, **60-80% of adults lack formal banking** — but they do have:
- 📱 Mobile money history (Wave, M-Pesa, Orange Money, MoMo)
- 📞 Telecom behavioral data
- 🛒 E-commerce transaction history
- 📍 Geolocation patterns

## API — Score a Business in Real-Time

```bash
curl -X POST https://api.your-domain.com/score   -H "Content-Type: application/json"   -d '{
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

**Response:**
```json
{
  "credit_score": 680,
  "risk_band": "B",
  "decision": "approved",
  "max_loan_amount_usd": 1500,
  "recommended_rate_pct": 12.0,
  "explanation": [
    "✅ High mobile money activity — strong financial engagement",
    "✅ Business established for 2.5 years",
    "✅ Regular income pattern detected"
  ]
}
```

## Stack

```
FastAPI          → REST API (scoring endpoint, <100ms latency)
Supabase         → PostgreSQL + RLS + real-time audit log
LightGBM         → ML scoring model (trained on historical repayment data)
dbt              → Feature engineering from raw transactions
```

## Countries Supported

Senegal 🇸🇳 · Côte d'Ivoire 🇨🇮 · Nigeria 🇳🇬 · Kenya 🇰🇪 · Ghana 🇬🇭 · Cameroon 🇨🇲

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env  # Add SUPABASE_URL, SUPABASE_KEY
supabase db push      # Apply migrations
uvicorn app.main:app --reload
```

## Author

**Ibrahima Gabar Diop** — [GitHub](https://github.com/Gblack98) · [Kaggle](https://www.kaggle.com/ibrahimagabardiop)
