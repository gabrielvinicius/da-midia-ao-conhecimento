import uuid


def generate_id() -> str:
    """Gera um identificador único usando UUID4.

    Returns:
        str: Um UUID no formato de string.

    """
    return str(uuid.uuid4())
