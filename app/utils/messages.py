from starlette.requests import Request

def flash(request: Request, message: str, category: str = "info") -> None:
    """Flash a message to the next request."""
    if "_messages" not in request.session:
        request.session["_messages"] = []
    request.session["_messages"].append({"message": message, "category": category})

def get_flashed_messages(request: Request):
    """Get all flashed messages and remove them from the session."""
    messages = request.session.pop("_messages") if "_messages" in request.session else []
    return messages