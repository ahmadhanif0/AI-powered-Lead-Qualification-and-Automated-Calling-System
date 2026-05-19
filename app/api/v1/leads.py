import csv
import io
import re
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional

from app.auth.dependencies import get_current_user
from app.models.user import User
from app.models.lead import Lead
from app.services.lead_scoring_service import LeadScoringService
from app.services.activity_logger import log_activity
from app.logs.logger import logger

router = APIRouter(prefix="/leads", tags=["Leads"])

MAX_ROWS      = 1000
MAX_FILE_SIZE = 5 * 1024 * 1024
EMAIL_RE      = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

_scorer = LeadScoringService()

REQUIRED_COLS = {"first_name", "email"}
TEMPLATE_COLS = ["first_name", "last_name", "email", "phone", "company", "lead_stage"]

VALID_STATUSES = {"Pending", "Booked", "Rejected", "Won't Follow Up"}
VALID_STAGES   = {"new", "contacted", "qualified", "interested",
                  "not_interested", "call_later", "wrong_number",
                  # HubSpot native stages also accepted
                  "lead", "subscriber", "marketingqualifiedlead",
                  "salesqualifiedlead", "opportunity", "customer"}

# Map HubSpot lifecyclestage → our internal stage
HS_STAGE_MAP = {
    "lead":                    "new",
    "subscriber":              "new",
    "marketingqualifiedlead":  "qualified",
    "salesqualifiedlead":      "qualified",
    "opportunity":             "interested",
    "customer":                "booked",
}


def infer_stage(email: str, phone: str, company: str, lead_stage: str = None) -> str:
    """
    Infer a sensible default stage from available contact data.
    If lead_stage is already set (e.g. from HubSpot), map it; otherwise derive from fields.
    """
    if lead_stage:
        return HS_STAGE_MAP.get(lead_stage.lower(), lead_stage)
    # Derive from data completeness
    has_email   = bool(email)
    has_phone   = bool(phone)
    has_company = bool(company)
    if has_email and has_phone and has_company:
        return "qualified"
    if has_email and has_phone:
        return "contacted"
    return "new"


# ── GET /leads/ ──────────────────────────────────────────────────────

@router.get("/")
async def list_leads(
    status:     Optional[str]   = None,
    lead_stage: Optional[str]   = None,
    score_min:  Optional[float] = None,
    score_max:  Optional[float] = None,
    search:     Optional[str]   = None,
    sort:       str             = "updated_at",
    order:      str             = "desc",
    page:       int             = Query(1, ge=1),
    page_size:  int             = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
):
    if current_user.role == "admin":
        qs = Lead.filter(user_id__isnull=False)
    else:
        qs = Lead.filter(user_id=current_user.id)

    if status:     qs = qs.filter(status=status)
    if lead_stage: qs = qs.filter(lead_stage=lead_stage)
    if score_min is not None: qs = qs.filter(score__gte=score_min)
    if score_max is not None: qs = qs.filter(score__lte=score_max)

    if search:
        from tortoise.expressions import Q
        qs = qs.filter(
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search)  |
            Q(email__icontains=search)      |
            Q(company__icontains=search)
        )

    valid_sorts = {"score", "created_at", "updated_at", "last_call_at"}
    sort_field  = sort if sort in valid_sorts else "updated_at"
    sort_expr   = f"-{sort_field}" if order == "desc" else sort_field

    total = await qs.count()
    leads = await qs.order_by(sort_expr).offset((page - 1) * page_size).limit(page_size)

    return {
        "total":     total,
        "page":      page,
        "page_size": page_size,
        "leads": [
            {
                "id":          l.id,
                "first_name":  l.first_name,
                "last_name":   l.last_name,
                "name":        f"{l.first_name or ''} {l.last_name or ''}".strip(),
                "email":       l.email,
                "phone":       l.phone,
                "company":     l.company,
                "score":       l.score,
                "status":      l.status,
                "stage":       l.lead_stage,
                "lead_stage":  l.lead_stage,
                "call_status": l.call_status,
                "ai_decision": l.ai_decision,
                "retry_count": l.retry_count,
                "updated_at":  l.updated_at.isoformat() if l.updated_at else None,
            }
            for l in leads
        ],
    }


# ── GET /leads/download-template ────────────────────────────────────

@router.get("/download-template")
async def download_template(_: User = Depends(get_current_user)):
    """Download a sample CSV template for lead import."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(TEMPLATE_COLS)
    writer.writerow(["Jane",  "Smith", "jane@acmecorp.com",  "+12025551234", "Acme Corp",  "lead"])
    writer.writerow(["John",  "Doe",   "john@example.com",   "+12025555678", "Example Ltd","subscriber"])
    output.seek(0)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=leads_template.csv"},
    )


# ── POST /leads/upload-csv ───────────────────────────────────────────

@router.post("/upload-csv")
async def upload_csv(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """
    Import leads from a CSV file.
    - Saves each row as a Lead in the database (user_id = current user).
    - If the user has HubSpot connected, also creates the contact in HubSpot.
    - Skips rows with duplicate email (per user).
    - Returns: {imported, skipped, hubspot_pushed, errors}
    """
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only .csv files are accepted")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File exceeds 5 MB limit")

    text   = content.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))

    if not reader.fieldnames:
        raise HTTPException(status_code=400, detail="CSV file is empty or has no headers")

    headers = {h.strip().lower() for h in reader.fieldnames}
    missing = REQUIRED_COLS - headers
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Missing required columns: {missing}. Required: {REQUIRED_COLS}"
        )

    rows = list(reader)
    if len(rows) > MAX_ROWS:
        raise HTTPException(status_code=400, detail=f"CSV exceeds {MAX_ROWS} row limit")

    # Try to get user's HubSpot client (optional — don't fail if not connected)
    hubspot_client = None
    try:
        from app.crm.hubspot_client import HubSpotClient
        hubspot_client = await HubSpotClient.for_user(current_user)
        logger.info(f"[CSV Import] HubSpot client available for user_id={current_user.id}")
    except Exception:
        logger.info(f"[CSV Import] No HubSpot connection for user_id={current_user.id} — skipping HubSpot push")

    imported        = 0
    skipped         = 0
    hubspot_pushed  = 0
    errors          = []

    for i, row in enumerate(rows, start=2):
        row = {k.strip().lower(): (v or "").strip() for k, v in row.items()}

        first_name = row.get("first_name", "")
        last_name  = row.get("last_name",  "")
        email      = row.get("email",      "")
        phone      = row.get("phone",      "")
        company    = row.get("company",    "")
        lead_stage = row.get("lead_stage", "")

        # Validation
        if not email:
            errors.append({"row": i, "reason": "email is required"})
            continue
        if not EMAIL_RE.match(email):
            errors.append({"row": i, "reason": f"invalid email: {email}"})
            continue
        if not first_name:
            errors.append({"row": i, "reason": "first_name is required"})
            continue

        # Duplicate check per user
        existing = await Lead.get_or_none(email=email, user_id=current_user.id)
        if existing:
            skipped += 1
            logger.debug(f"[CSV Import] Skipped duplicate email={email} for user_id={current_user.id}")
            continue

        # ── Save to DB ───────────────────────────────────────────────
        try:
            # Infer stage if not provided in CSV
            resolved_stage = infer_stage(email, phone, company, lead_stage or None)

            # Calculate score from available CSV fields
            score = _scorer.calculate_score({
                "email":      email,
                "phone":      phone      or None,
                "company":    company    or None,
                "lead_stage": resolved_stage,
            })

            # Synthetic scoped hubspot_id for CSV-imported leads
            synthetic_id = f"csv_{current_user.id}_{email}"

            new_lead = await Lead.create(
                user_id=current_user.id,
                hubspot_id=synthetic_id,
                first_name=first_name,
                last_name=last_name    or None,
                email=email,
                phone=phone            or None,
                company=company        or None,
                lead_stage=resolved_stage,
                score=score,
            )
            imported += 1
            logger.info(
                f"[CSV Import] Saved lead id={new_lead.id} "
                f"name={first_name} {last_name} email={email} "
                f"stage={resolved_stage} score={score} user_id={current_user.id}"
            )
        except Exception as e:
            errors.append({"row": i, "reason": f"DB error: {e}"})
            logger.error(f"[CSV Import] DB error row {i} email={email}: {e}")
            continue

        # ── Push to HubSpot (if connected) ───────────────────────────
        if hubspot_client:
            try:
                hs_contact = await hubspot_client.create_contact({
                    "firstname":      first_name,
                    "lastname":       last_name       or "",
                    "email":          email,
                    "phone":          phone           or "",
                    "company":        company         or "",
                    "lifecyclestage": lead_stage      or "lead",
                })
                hs_id = hs_contact.get("id")
                hubspot_pushed += 1

                # Update the lead's hubspot_id with the real HubSpot ID
                # so future syncs can match and update it correctly
                if hs_id:
                    scoped_hs_id = f"{current_user.id}_{hs_id}"
                    new_lead.hubspot_id = scoped_hs_id
                    await new_lead.save()

                logger.info(
                    f"[CSV Import] Pushed to HubSpot: contact_id={hs_id} "
                    f"email={email} user_id={current_user.id}"
                )
            except Exception as e:
                # HubSpot push failure is non-fatal — lead is already in DB
                logger.warning(
                    f"[CSV Import] HubSpot push failed for email={email}: {e} "
                    "(lead saved to DB, not pushed to HubSpot)"
                )

    await log_activity(
        current_user.id,
        "csv_import",
        {
            "imported":       imported,
            "skipped":        skipped,
            "hubspot_pushed": hubspot_pushed,
            "errors":         len(errors),
        },
    )

    logger.info(
        f"[CSV Import] Complete for user_id={current_user.id} — "
        f"imported={imported}, skipped={skipped}, "
        f"hubspot_pushed={hubspot_pushed}, errors={len(errors)}"
    )

    return {
        "imported":       imported,
        "skipped":        skipped,
        "hubspot_pushed": hubspot_pushed,
        "errors":         errors[:20],
    }


# ── GET /leads/{lead_id} ─────────────────────────────────────────────

@router.get("/{lead_id}")
async def get_lead(
    lead_id: int,
    current_user: User = Depends(get_current_user),
):
    lead = await Lead.get_or_none(id=lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    if current_user.role != "admin" and lead.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    return {
        "id":             lead.id,
        "first_name":     lead.first_name,
        "last_name":      lead.last_name,
        "name":           f"{lead.first_name or ''} {lead.last_name or ''}".strip(),
        "email":          lead.email,
        "phone":          lead.phone,
        "company":        lead.company,
        "lead_stage":     lead.lead_stage,
        "score":          lead.score,
        "status":         lead.status,
        "call_status":    lead.call_status,
        "ai_decision":    lead.ai_decision,
        "last_transcript":lead.last_transcript,
        "retry_count":    lead.retry_count,
        "hubspot_id":     lead.hubspot_id,
        "user_id":        lead.user_id,
        "created_at":     lead.created_at.isoformat() if lead.created_at else None,
        "updated_at":     lead.updated_at.isoformat() if lead.updated_at else None,
    }


# ── PUT /leads/{lead_id} ─────────────────────────────────────────────

from pydantic import BaseModel

class UpdateLeadRequest(BaseModel):
    """Contact info fields + optional manual status override."""
    first_name: Optional[str] = None
    last_name:  Optional[str] = None
    email:      Optional[str] = None
    phone:      Optional[str] = None
    company:    Optional[str] = None
    status:     Optional[str] = None   # manual override: Pending/Booked/Rejected/Won't Follow Up


class CreateLeadRequest(BaseModel):
    """Stage is always auto-inferred — never accepted from the client."""
    first_name: str
    last_name:  Optional[str] = None
    email:      str
    phone:      Optional[str] = None
    company:    Optional[str] = None
    # Admin-only: assign to a specific user
    assign_to_user_id: Optional[int] = None


# ── POST /leads/create ───────────────────────────────────────────────

@router.post("/create", status_code=201)
async def create_lead(
    body: CreateLeadRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Manually create a single lead.
    - Saves to DB with user_id = current_user.id (or assign_to_user_id for admins).
    - Calculates score immediately.
    - Infers stage from available data.
    - Pushes to HubSpot if user has a connected CRM.
    """
    # Validate email
    if not EMAIL_RE.match(body.email):
        raise HTTPException(status_code=400, detail=f"Invalid email: {body.email}")

    # Determine owner
    owner_id = current_user.id
    if body.assign_to_user_id and current_user.role == "admin":
        owner_id = body.assign_to_user_id

    # Duplicate check per user
    existing = await Lead.get_or_none(email=body.email, user_id=owner_id)
    if existing:
        raise HTTPException(status_code=409, detail=f"A lead with email {body.email} already exists")

    # Infer stage — CreateLeadRequest has no lead_stage field; always auto-detect
    resolved_stage = infer_stage(
        body.email, body.phone or "", body.company or "", None
    )

    # Calculate score
    score = _scorer.calculate_score({
        "email":      body.email,
        "phone":      body.phone,
        "company":    body.company,
        "lead_stage": resolved_stage,
    })

    # Save to DB
    synthetic_id = f"manual_{owner_id}_{body.email}"
    new_lead = await Lead.create(
        user_id=owner_id,
        hubspot_id=synthetic_id,
        first_name=body.first_name,
        last_name=body.last_name  or None,
        email=body.email,
        phone=body.phone          or None,
        company=body.company      or None,
        lead_stage=resolved_stage,
        score=score,
    )

    logger.info(
        f"[Create Lead] id={new_lead.id} email={body.email} "
        f"stage={resolved_stage} score={score} user_id={owner_id}"
    )

    # Push to HubSpot if connected
    hubspot_pushed = False
    hubspot_error: str | None = None
    try:
        from app.models.user import User as UserModel
        from app.crm.hubspot_client import HubSpotClient

        # Use the owner's HubSpot connection (not necessarily current_user if admin assigned)
        owner = await UserModel.get(id=owner_id)
        logger.info(f"[Create Lead] Attempting HubSpot push for owner_id={owner_id} email={body.email}")

        hs_client = await HubSpotClient.for_user(owner)
        logger.info(f"[Create Lead] HubSpot client obtained for owner_id={owner_id}")

        contact_payload = {
            "firstname":      body.first_name,
            "lastname":       body.last_name   or "",
            "email":          body.email,
            "phone":          body.phone       or "",
            "company":        body.company     or "",
            "lifecyclestage": resolved_stage,
        }
        logger.info(f"[Create Lead] Sending to HubSpot: {contact_payload}")

        hs_contact = await hs_client.create_contact(contact_payload)
        hs_id = hs_contact.get("id")
        if hs_id:
            new_lead.hubspot_id = f"{owner_id}_{hs_id}"
            await new_lead.save()
        hubspot_pushed = True
        logger.info(f"[Create Lead] HubSpot push SUCCESS contact_id={hs_id} email={body.email}")

    except ValueError as e:
        # HubSpot not connected — expected, non-fatal
        hubspot_error = str(e)
        logger.info(f"[Create Lead] HubSpot not connected for owner_id={owner_id}: {e}")
    except Exception as e:
        # Unexpected error — log as error so it's visible
        hubspot_error = str(e)
        logger.error(
            f"[Create Lead] HubSpot push FAILED for email={body.email} owner_id={owner_id}: "
            f"{type(e).__name__}: {e}"
        )

    await log_activity(current_user.id, "create_lead", {
        "lead_id": new_lead.id, "email": body.email, "hubspot_pushed": hubspot_pushed
    })

    return {
        "id":             new_lead.id,
        "first_name":     new_lead.first_name,
        "last_name":      new_lead.last_name,
        "email":          new_lead.email,
        "phone":          new_lead.phone,
        "company":        new_lead.company,
        "lead_stage":     new_lead.lead_stage,
        "score":          new_lead.score,
        "status":         new_lead.status,
        "hubspot_id":     new_lead.hubspot_id,
        "hubspot_pushed": hubspot_pushed,
        "hubspot_error":  hubspot_error,
    }


@router.put("/{lead_id}")
async def update_lead(
    lead_id: int,
    body: UpdateLeadRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Update contact info only (name, email, phone, company).
    Stage and status are system-controlled — they are NEVER changed here.
    Score is recalculated from the updated contact info.
    """
    lead = await Lead.get_or_none(id=lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    if current_user.role != "admin" and lead.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Apply only the allowed contact-info fields
    allowed = {"first_name", "last_name", "email", "phone", "company"}
    update_data = {k: v for k, v in body.model_dump(exclude_none=True).items() if k in allowed}
    logger.info(f"[Lead Update] lead_id={lead_id} update_data={update_data}")
    for field, value in update_data.items():
        setattr(lead, field, value)

    # Apply manual status override if provided and valid
    if body.status:
        if body.status not in VALID_STATUSES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status '{body.status}'. Must be one of: {sorted(VALID_STATUSES)}"
            )
        lead.status = body.status
        logger.info(f"[Lead Update] Manual status override: lead {lead_id} → {body.status}")

    # Recalculate score — keep existing lead_stage (system-controlled)
    lead.score = _scorer.calculate_score({
        "email":      lead.email,
        "phone":      lead.phone,
        "company":    lead.company,
        "lead_stage": lead.lead_stage,
    })

    await lead.save()

    # Sync contact info to HubSpot if the lead has a real HubSpot contact ID.
    # Synthetic placeholder IDs (csv_*, manual_*) mean the lead was never
    # pushed to HubSpot, so there's nothing to update there.
    # Once a lead is pushed, hubspot_id becomes "{user_id}_{hs_contact_id}",
    # which does NOT start with "csv_" or "manual_", so sync runs correctly.
    has_real_hs_id = (
        lead.hubspot_id
        and not lead.hubspot_id.startswith("csv_")
        and not lead.hubspot_id.startswith("manual_")
    )
    if not has_real_hs_id:
        logger.info(
            f"[Lead Update] Skipping HubSpot sync for lead {lead_id} — "
            f"hubspot_id='{lead.hubspot_id}' is a synthetic placeholder "
            f"(lead was never pushed to HubSpot)"
        )
    else:
        try:
            from app.crm.hubspot_client import HubSpotClient
            hs_client = await HubSpotClient.for_user(current_user)
            raw_hs_id = lead.hubspot_id.split("_", 1)[-1]
            await hs_client.update_contact(raw_hs_id, {
                "firstname": lead.first_name or "",
                "lastname":  lead.last_name  or "",
                "email":     lead.email      or "",
                "phone":     lead.phone      or "",
                "company":   lead.company    or "",
            })
            logger.info(f"[Lead Update] HubSpot contact updated for lead {lead_id}")
        except Exception as e:
            logger.warning(f"[Lead Update] HubSpot sync failed for lead {lead_id}: {e}")

    await log_activity(current_user.id, "update_lead", {
        "lead_id": lead_id, "updated_fields": list(update_data.keys())
    })

    return {
        "id":         lead.id,
        "first_name": lead.first_name,
        "last_name":  lead.last_name,
        "email":      lead.email,
        "phone":      lead.phone,
        "company":    lead.company,
        "lead_stage": lead.lead_stage,   # returned for display, not editable
        "status":     lead.status,       # returned for display, not editable
        "ai_decision":lead.ai_decision,  # returned for display
        "score":      lead.score,
        "updated_at": lead.updated_at.isoformat() if lead.updated_at else None,
    }


# ── DELETE /leads/{lead_id} ──────────────────────────────────────────

@router.delete("/{lead_id}")
async def delete_lead(
    lead_id: int,
    current_user: User = Depends(get_current_user),
):
    lead = await Lead.get_or_none(id=lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    if current_user.role != "admin" and lead.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Delete from HubSpot if it has a real HubSpot ID (not CSV-synthetic)
    if lead.hubspot_id and not lead.hubspot_id.startswith("csv_"):
        try:
            from app.crm.hubspot_client import HubSpotClient
            hs_client = await HubSpotClient.for_user(current_user)
            raw_hs_id = lead.hubspot_id.split("_", 1)[-1]
            # Archive the contact in HubSpot (soft delete)
            await hs_client._request(
                "DELETE",
                f"{hs_client.BASE_URL}/crm/v3/objects/contacts/{raw_hs_id}"
            )
            logger.info(f"[Lead Delete] Archived HubSpot contact {raw_hs_id} for lead {lead_id}")
        except Exception as e:
            logger.warning(f"[Lead Delete] HubSpot delete failed for lead {lead_id}: {e} — deleting locally anyway")

    await lead.delete()
    await log_activity(current_user.id, "delete_lead", {"lead_id": lead_id})

    return {"message": "Lead deleted successfully"}
