import json

from encrypted_fields.fields import EncryptedTextField


class EncryptedJSONField(EncryptedTextField):
    """JSON serialized into the existing SENSD Fernet-encrypted text field."""

    description = "Encrypted JSON"

    def get_prep_value(self, value):
        if value is not None and not isinstance(value, str):
            value = json.dumps(value, separators=(",", ":"), default=str)
        return super().get_prep_value(value)

    def from_db_value(self, value, expression, connection):
        value = super().from_db_value(value, expression, connection)
        if value in (None, "") or not isinstance(value, str):
            return value
        try:
            return json.loads(value)
        except (TypeError, ValueError):
            return value
