def success_response(data, message: str | None = None) -> dict:
    payload = {"success": True, "data": data}
    if message:
        payload["message"] = message
    return payload

