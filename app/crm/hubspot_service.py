from app.crm.hubspot_client import HubSpotClient


class HubSpotService:
    def __init__(self):
        self.client = HubSpotClient()

    async def fetch_contacts(self):
        all_contacts = []
        after = None

        while True:
            response = await self.client.get_contacts(after=after)

            results = response.get("results", [])

            all_contacts.extend(results)

            paging = response.get("paging")

            if not paging:
                break

            after = paging["next"]["after"]

        return all_contacts