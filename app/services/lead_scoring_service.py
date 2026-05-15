from datetime import datetime, timezone, timedelta


# Keywords that suggest an established / formal company
COMPANY_KEYWORDS = ["inc", "llc", "corp", "ltd", "limited", "group", "holdings"]


class LeadScoringService:

    def calculate_score(self, lead_data: dict) -> float:
        """
        Composite lead score (0–100).

        Factors
        -------
        Base                    +10  (every lead)
        Company present         +20
        Company value signals   +5 / +10
        Business email          +15  (non-Gmail)
        Personal email          +5
        Phone present           +10
        Lead stage              +10 / +25 / +40 / +60
        Lead freshness          +15 / +10 / +5
        Previous engagement     +20 / +5 / -5 per retry
        Business hours          +5
        """

        score = 0.0
        now   = datetime.now(timezone.utc)

        # --------------------------------------------------
        # 1. BASE
        # --------------------------------------------------
        score += 10

        # --------------------------------------------------
        # 2. COMPANY PRESENCE
        # --------------------------------------------------
        company = (lead_data.get("company") or "").strip()

        if company:
            score += 20

            # 3. COMPANY VALUE SIGNALS
            company_lower = company.lower()

            # Formal entity keywords → established business
            if any(kw in company_lower for kw in COMPANY_KEYWORDS):
                score += 10
            elif len(company) > 20:
                # Long company name is a proxy for an established org
                score += 5

        # --------------------------------------------------
        # 4. EMAIL QUALITY
        # --------------------------------------------------
        email = lead_data.get("email") or ""

        if email:
            if not email.lower().endswith("@gmail.com"):
                score += 15   # business email
            else:
                score += 5    # personal email — still has contact info

        # --------------------------------------------------
        # 5. PHONE PRESENCE
        # --------------------------------------------------
        if lead_data.get("phone"):
            score += 10

        # --------------------------------------------------
        # 6. LEAD STAGE
        # --------------------------------------------------
        stage = (lead_data.get("lead_stage") or "").lower()

        if stage in ["lead", "subscriber"]:
            score += 10
        elif stage in ["marketingqualifiedlead", "mql"]:
            score += 25
        elif stage in ["salesqualifiedlead", "sql"]:
            score += 40
        elif stage in ["opportunity"]:
            score += 60

        # --------------------------------------------------
        # 7. LEAD FRESHNESS
        # created_at may be a datetime object or ISO string.
        # --------------------------------------------------
        created_at = lead_data.get("created_at")

        if created_at:
            if isinstance(created_at, str):
                try:
                    created_at = datetime.fromisoformat(
                        created_at.replace("Z", "+00:00")
                    )
                except ValueError:
                    created_at = None

            if created_at:
                age = now - created_at
                if age <= timedelta(hours=24):
                    score += 15   # very fresh — highest priority
                elif age <= timedelta(days=7):
                    score += 10
                elif age <= timedelta(days=30):
                    score += 5

        # --------------------------------------------------
        # 8. PREVIOUS ENGAGEMENT
        # --------------------------------------------------
        # Positive: previous "Interested" decision
        ai_decision = (lead_data.get("ai_decision") or "").lower()
        if ai_decision == "interested":
            score += 20

        # Positive: called within last 7 days (recent engagement)
        last_call_at = lead_data.get("last_call_at")
        if last_call_at:
            if isinstance(last_call_at, str):
                try:
                    last_call_at = datetime.fromisoformat(
                        last_call_at.replace("Z", "+00:00")
                    )
                except ValueError:
                    last_call_at = None

            if last_call_at and (now - last_call_at) <= timedelta(days=7):
                score += 5

        # Negative: each retry attempt shows disengagement
        retry_count = lead_data.get("retry_count") or 0
        score -= retry_count * 5

        # --------------------------------------------------
        # 9. TIMEZONE / BUSINESS HOURS FACTOR
        # Adds +5 if the current local hour is 9am–5pm.
        # Replace with proper per-lead timezone logic when
        # phone number country codes are available.
        # --------------------------------------------------
        current_hour = now.hour  # UTC hour as baseline

        if 9 <= current_hour < 17:
            score += 5

        # --------------------------------------------------
        # CLAMP to [0, 100]
        # --------------------------------------------------
        return round(min(max(score, 0.0), 100.0), 2)
