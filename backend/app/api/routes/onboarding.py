"""
Routes onboarding — Questionnaire profil de risque.
POST /onboarding/questionnaire : Calcule et sauvegarde le profil
GET  /onboarding/profile       : Retourne le profil actuel
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.db.postgres import get_db
from app.models.user import User, RiskProfile

router = APIRouter()


# ── Schémas ──────────────────────────────────────────────────

class QuestionnaireRequest(BaseModel):
    """
    5 questions, score 1–5 chacune.
    1. Horizon d'investissement    (< 1 an = 1, > 10 ans = 5)
    2. Réaction à une baisse -20% (vendre tout = 1, acheter plus = 5)
    3. % capital investi           (< 10% = 1, > 75% = 5)
    4. Connaissance des marchés   (débutant = 1, expert = 5)
    5. Objectif principal          (préserver = 1, maximiser = 5)
    """
    q1_horizon: int
    q2_reaction_baisse: int
    q3_pct_capital: int
    q4_connaissance: int
    q5_objectif: int

    @field_validator("q1_horizon", "q2_reaction_baisse", "q3_pct_capital", "q4_connaissance", "q5_objectif")
    @classmethod
    def validate_score(cls, v: int) -> int:
        if not 1 <= v <= 5:
            raise ValueError("Chaque réponse doit être comprise entre 1 et 5.")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "q1_horizon": 4,
                "q2_reaction_baisse": 3,
                "q3_pct_capital": 3,
                "q4_connaissance": 2,
                "q5_objectif": 3,
            }
        }
    }


class ProfileResponse(BaseModel):
    id: str
    score: int
    profile_type: str
    questionnaire_answers: dict

    model_config = {"from_attributes": True}


# ── Logique de scoring ────────────────────────────────────────

def compute_risk_profile(answers: dict) -> tuple[int, str]:
    """
    Calcule le score total et le type de profil.
    Score 5–12  → conservateur
    Score 13–19 → modéré
    Score 20–25 → agressif
    """
    total = sum(answers.values())

    if 5 <= total <= 12:
        profile_type = "conservateur"
    elif 13 <= total <= 19:
        profile_type = "modéré"
    else:
        profile_type = "agressif"

    return total, profile_type


# ── Routes ───────────────────────────────────────────────────

@router.post(
    "/questionnaire",
    response_model=ProfileResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Soumettre le questionnaire de profil de risque",
)
async def submit_questionnaire(
    payload: QuestionnaireRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Calcule le profil de risque côté backend (jamais côté frontend).
    Sauvegarde le nouveau profil en base.
    """
    answers = payload.model_dump()
    score, profile_type = compute_risk_profile(answers)

    profile = RiskProfile(
        user_id=current_user.id,
        score=score,
        profile_type=profile_type,
        questionnaire_answers=answers,
    )
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return profile


@router.get(
    "/profile",
    response_model=ProfileResponse,
    summary="Récupérer le profil de risque actuel",
)
async def get_profile(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retourne le dernier profil de risque de l'utilisateur."""
    result = await db.execute(
        select(RiskProfile)
        .where(RiskProfile.user_id == current_user.id)
        .order_by(RiskProfile.created_at.desc())
        .limit(1)
    )
    profile = result.scalar_one_or_none()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aucun profil de risque trouvé. Veuillez compléter le questionnaire.",
        )
    return profile
