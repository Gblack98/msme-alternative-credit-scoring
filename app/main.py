"""
MSME Alternative Credit Scoring API
FastAPI + Supabase + ML — inspired by Rubyx.io

Scores micro/small businesses in Africa using alternative data:
- Mobile money transaction history
- Telecom behavioral data (airtime usage patterns)
- E-commerce activity
- Social network signals
"""

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List
import os
from datetime import datetime

app = FastAPI(
    title="MSME Alternative Credit Scoring API",
    description="Real-time credit scoring for micro/small businesses using alternative data",
    version="1.0.0",
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# ── Schemas ────────────────────────────────────────────────────────────────

class MobileMoneySummary(BaseModel):
    """Summary of mobile money activity (MoMo, M-Pesa, Wave, Orange Money)"""
    total_transactions_90d: int = Field(..., ge=0, description="Number of transactions in last 90 days")
    total_volume_usd_90d: float = Field(..., ge=0)
    avg_transaction_usd: float = Field(..., ge=0)
    unique_counterparties: int = Field(..., ge=0)
    days_since_last_transaction: int = Field(..., ge=0)
    receives_salary: bool = False
    has_regular_income: bool = False


class BusinessProfile(BaseModel):
    """MSME profile for credit scoring"""
    business_id: str
    country_code: str = Field(..., description="ISO 2-letter code: SN, CI, NG, KE, GH...")
    sector: str = Field(..., description="retail, agriculture, services, manufacturing, transport")
    years_in_operation: float = Field(..., ge=0)
    monthly_revenue_usd: Optional[float] = None
    employee_count: int = Field(default=1, ge=1)
    has_bank_account: bool = False
    has_tax_id: bool = False
    mobile_money: Optional[MobileMoneySummary] = None
    requested_amount_usd: float = Field(..., gt=0)
    loan_purpose: str = Field(..., description="working_capital, equipment, inventory, expansion")


class ScoreResponse(BaseModel):
    """Credit score response"""
    business_id: str
    credit_score: int = Field(..., ge=300, le=850, description="FICO-style score")
    default_probability: float = Field(..., ge=0, le=1)
    risk_band: str = Field(..., description="A (excellent) to D (high risk)")
    max_loan_amount_usd: float
    recommended_rate_pct: float
    decision: str = Field(..., description="approved / review / declined")
    explanation: List[str] = Field(..., description="Top factors influencing the score")
    scored_at: datetime
    model_version: str


# ── Feature Engineering ────────────────────────────────────────────────────

def extract_features(profile: BusinessProfile) -> dict:
    """Transform BusinessProfile into ML features"""
    features = {
        # Business fundamentals
        'years_in_operation': profile.years_in_operation,
        'employee_count': profile.employee_count,
        'monthly_revenue_usd': profile.monthly_revenue_usd or 0,
        'has_bank_account': int(profile.has_bank_account),
        'has_tax_id': int(profile.has_tax_id),

        # Loan request ratios
        'loan_to_monthly_revenue': (
            profile.requested_amount_usd / profile.monthly_revenue_usd
            if profile.monthly_revenue_usd and profile.monthly_revenue_usd > 0 else 10.0
        ),

        # Mobile money features (alternative data — key for unbanked)
        'momo_tx_count_90d': 0,
        'momo_volume_90d': 0,
        'momo_avg_tx': 0,
        'momo_unique_counterparties': 0,
        'momo_recency': 999,
        'momo_has_regular_income': 0,
        'momo_receives_salary': 0,

        # Sector encoding (simplified)
        'sector_is_retail': int(profile.sector == 'retail'),
        'sector_is_agriculture': int(profile.sector == 'agriculture'),
        'sector_is_services': int(profile.sector == 'services'),
    }

    if profile.mobile_money:
        m = profile.mobile_money
        features.update({
            'momo_tx_count_90d': m.total_transactions_90d,
            'momo_volume_90d': m.total_volume_usd_90d,
            'momo_avg_tx': m.avg_transaction_usd,
            'momo_unique_counterparties': m.unique_counterparties,
            'momo_recency': m.days_since_last_transaction,
            'momo_has_regular_income': int(m.has_regular_income),
            'momo_receives_salary': int(m.receives_salary),
        })

    return features


def score_to_decision(score: int, probability: float, requested: float) -> tuple:
    """Convert score to business decision"""
    if score >= 700:
        band, decision = 'A', 'approved'
        max_loan = requested * 1.2
        rate = 8.0
    elif score >= 600:
        band, decision = 'B', 'approved'
        max_loan = requested
        rate = 12.0
    elif score >= 500:
        band, decision = 'C', 'review'
        max_loan = requested * 0.7
        rate = 18.0
    else:
        band, decision = 'D', 'declined'
        max_loan = 0
        rate = 0

    return band, decision, max_loan, rate


def generate_explanation(features: dict, score: int) -> List[str]:
    """Generate human-readable explanation (GDPR right to explanation)"""
    reasons = []

    if features['momo_tx_count_90d'] > 30:
        reasons.append("✅ High mobile money activity — strong financial engagement")
    elif features['momo_tx_count_90d'] < 5:
        reasons.append("⚠️ Low mobile money activity — limited transaction history")

    if features['years_in_operation'] >= 2:
        reasons.append(f"✅ Business established for {features['years_in_operation']:.1f} years")
    else:
        reasons.append("⚠️ New business — limited operating history increases risk")

    if features['has_bank_account']:
        reasons.append("✅ Has formal bank account")

    if features['loan_to_monthly_revenue'] > 5:
        reasons.append("⚠️ Requested amount is high relative to monthly revenue")
    elif features['loan_to_monthly_revenue'] < 2:
        reasons.append("✅ Loan amount well-proportioned to monthly revenue")

    if features['momo_has_regular_income']:
        reasons.append("✅ Regular income pattern detected in mobile money history")

    return reasons[:4]  # Top 4 factors


# ── Endpoints ──────────────────────────────────────────────────────────────

@app.post("/score", response_model=ScoreResponse)
async def score_business(profile: BusinessProfile, background_tasks: BackgroundTasks):
    """
    Score an MSME for credit risk.
    Returns credit score (300-850), risk band, max loan amount, and explanation.
    """
    try:
        features = extract_features(profile)

        # TODO: load real model
        # model = joblib.load("models/msme_scorer_v1.pkl")
        # proba = model.predict_proba([list(features.values())])[0][1]

        # Placeholder scoring logic (replace with trained model)
        score_components = (
            min(features['momo_tx_count_90d'] / 100, 1.0) * 150 +
            min(features['years_in_operation'] / 5, 1.0) * 100 +
            int(features['has_bank_account']) * 80 +
            int(features['momo_has_regular_income']) * 70 +
            (1 - min(features['loan_to_monthly_revenue'] / 10, 1.0)) * 100 +
            min(features['momo_volume_90d'] / 5000, 1.0) * 50
        )
        credit_score = int(300 + score_components)
        proba = max(0.0, min(1.0, 1 - (credit_score - 300) / 550))

        band, decision, max_loan, rate = score_to_decision(credit_score, proba, profile.requested_amount_usd)
        explanation = generate_explanation(features, credit_score)

        # Log to Supabase in background (non-blocking)
        background_tasks.add_task(log_score_to_supabase, profile.business_id, credit_score, proba, band)

        return ScoreResponse(
            business_id=profile.business_id,
            credit_score=credit_score,
            default_probability=round(proba, 4),
            risk_band=band,
            max_loan_amount_usd=round(max_loan, 2),
            recommended_rate_pct=rate,
            decision=decision,
            explanation=explanation,
            scored_at=datetime.utcnow(),
            model_version="1.0.0",
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def log_score_to_supabase(business_id: str, score: int, proba: float, band: str):
    """Log scoring event to Supabase for audit trail and model monitoring"""
    # TODO: implement Supabase client
    # from supabase import create_client
    # supabase = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_KEY'])
    # supabase.table('scoring_logs').insert({...}).execute()
    pass


@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}
