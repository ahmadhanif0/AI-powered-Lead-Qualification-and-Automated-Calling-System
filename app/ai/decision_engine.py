class DecisionEngine:

    def analyze(self, transcript: str):

        transcript = transcript.lower()

        # ---- Wrong Number (check before anything else) ----
        wrong_number_keywords = [
            "wrong number",
            "you got wrong person",
            "wrong person",
            "not the right number",
        ]
        for keyword in wrong_number_keywords:
            if keyword in transcript:
                return "Wrong Number"

        # ---- Not Interested ----
        not_interested_keywords = [
            "not interested",
            "don't call",
            "do not call",
            "stop calling",
            "remove me",
            "take me off",
            "no thank you",
            "no thanks",
            # Negative / dismissive phrases
            "not helpful",
            "that's not helpful",
            "this is not helpful",
            "not useful",
            "not relevant",
            "don't need this",
            "do not need this",
            "don't want this",
            "do not want this",
            "not for me",
            "not what i need",
            "not what i'm looking for",
            "not looking for this",
            "not interested in this",
            "waste of time",
            "please don't call",
            "never call again",
            "don't contact me",
        ]
        for keyword in not_interested_keywords:
            if keyword in transcript:
                return "Not Interested"

        # ---- Call Later ----
        call_later_keywords = [
            "call later",
            "call me later",
            "call back later",
            "another time",
            "not a good time",
            "i'm busy",
            "i am busy",
            "call me back",
        ]
        for keyword in call_later_keywords:
            if keyword in transcript:
                return "Call Later"

        # ---- Interested ----
        # Replaced broad single-word matches ("yes", "customers",
        # "marketing") with specific phrases to reduce false positives.
        interested_keywords = [
            "yes i'm interested",
            "yes i am interested",
            "i'm interested",
            "i am interested",
            "sounds interesting",
            "grow my business",
            "looking to expand",
            "want more sales",
            "need more customers",
            "interested in marketing",
            "interested in growing",
            "online business",
            "beauty products",
            "tell me more",
            "how does it work",
            "what's the price",
            "what is the price",
            "sign me up",
            "let's do it",
            "let's go ahead",
        ]
        for keyword in interested_keywords:
            if keyword in transcript:
                return "Interested"

        return "No Response"
