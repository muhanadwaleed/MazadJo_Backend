"""Write audit log rows for staff and seller lifecycle actions."""

from audit.models import AuditLog


def log_audit(
    *,
    actor,
    entity_type: str,
    entity_id: int,
    action: str,
    old_values=None,
    new_values=None,
    request=None,
) -> AuditLog:
    ip_address = None
    user_agent = ""
    if request is not None:
        ip_address = request.META.get("REMOTE_ADDR")
        user_agent = (request.META.get("HTTP_USER_AGENT") or "")[:512]

    return AuditLog.objects.create(
        actor_user=actor if getattr(actor, "is_authenticated", False) else None,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        old_values_json=old_values,
        new_values_json=new_values,
        ip_address=ip_address,
        user_agent=user_agent,
    )
