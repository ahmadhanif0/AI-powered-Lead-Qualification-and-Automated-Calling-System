class AIConversationScoringService:

    def calculate_score(self, transcript: str, decision: str):

        transcript = transcript.lower()

        score = 0

        # -------------------------
        # Decision Based Score
        # -------------------------

        if decision == "Interested":
            score += 40

        elif decision == "Call Later":
            score += 15

        elif decision == "Not Interested":
            score -= 25

        elif decision == "Wrong Number":
            score -= 50

        # -------------------------
        # Urgency Detection
        # -------------------------

        urgency_keywords = [
            "urgent",
            "asap",
            "immediately",
            "this week",
            "today"
        ]

        for keyword in urgency_keywords:
            if keyword in transcript:
                score += 20
                break

        # -------------------------
        # Budget / Buying Intent
        # -------------------------

        buying_keywords = [
            "budget",
            "price",
            "cost",
            "purchase",
            "buy",
            "investment"
        ]

        for keyword in buying_keywords:
            if keyword in transcript:
                score += 15
                break

        # -------------------------
        # Strong Interest
        # -------------------------

        strong_interest_keywords = [
            "very interested",
            "sounds good",
            "let's do it",
            "need this",
            "want this"
        ]

        for keyword in strong_interest_keywords:
            if keyword in transcript:
                score += 25
                break

        # -------------------------
        # Negative Sentiment
        # -------------------------

        negative_keywords = [
            "stop calling",
            "not interested",
            "remove me",
            "busy forever"
        ]

        for keyword in negative_keywords:
            if keyword in transcript:
                score -= 30
                break

        # clamp score
        score = max(min(score, 100), -100)

        return score