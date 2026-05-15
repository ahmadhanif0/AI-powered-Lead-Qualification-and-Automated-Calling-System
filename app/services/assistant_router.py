from app.services.assistant_service import AssistantService


class AssistantRouter:

    def __init__(self):
        self.service = AssistantService()

    async def select_assistant(self, lead: dict):

        score = lead.get("score", 0)
        stage = (lead.get("lead_stage") or "").lower()

        assistants = await self.service.list_assistants()

        # Default fallback
        default_assistant = assistants[0] if assistants else None

        if not default_assistant:
            raise Exception("No assistants found")

        # High value lead → aggressive assistant
        if score >= 70 or stage in ["opportunity", "sql"]:
            for a in assistants:
                if "sales" in a.name.lower():
                    return a

        # Medium lead → normal assistant
        if score >= 40:
            for a in assistants:
                if "growth" in a.name.lower():
                    return a

        # Low lead → nurturing assistant
        for a in assistants:
            if "support" in a.name.lower():
                return a

        return default_assistant