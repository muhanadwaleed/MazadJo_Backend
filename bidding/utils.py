def mask_username(username: str) -> str:
    if not username:
        return "***"
    u = username.strip()
    if len(u) <= 2:
        return "***"
    return f"{u[:2]}***"
