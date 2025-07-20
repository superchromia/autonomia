from external.nebius import NebiusAIStudioClient

def get_nebius_client(model_id: str) -> NebiusAIStudioClient:
    return NebiusAIStudioClient(model_id) 