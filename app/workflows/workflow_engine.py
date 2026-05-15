from app.workflows.actions import WorkflowActions


class WorkflowEngine:

    def __init__(self):
        self.actions = WorkflowActions()

    async def handle_result(self, lead: dict, result: str):

        # Normalise to lowercase with spaces so it matches
        # DecisionEngine output: "Interested", "Call Later",
        # "Not Interested", "Wrong Number", "No Response"
        result = result.lower().strip()

        if result == "interested":
            return await self.actions.handle_interested(lead)

        # "Call Later" → "call later"  (was wrongly "call_later")
        if result == "call later":
            return await self.actions.handle_call_later(lead)

        # "Not Interested" → "not interested"
        if result == "not interested":
            return await self.actions.handle_not_interested(lead)

        # "Wrong Number" → "wrong number"
        if result == "wrong number":
            return await self.actions.handle_wrong_number(lead)

        # "No Response" → "no response"  (and any unknown fallback)
        return await self.actions.handle_no_response(lead)