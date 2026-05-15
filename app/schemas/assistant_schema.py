from pydantic import BaseModel


class CreateAssistantSchema(BaseModel):

    name: str

    system_prompt: str

    first_message: str

    voice_id: str = "Elliot"

    model_provider: str = "openai"

    model_name: str = "gpt-4.1"