# sensd/fields.py
from encrypted_fields.fields import EncryptedBooleanField

_TRUTHY = {"1","true","t","yes","y","on"}
_FALSY  = {"0","false","f","no","n","off",""}

class CoercedEncryptedBooleanField(EncryptedBooleanField):
    """
    EncryptedBooleanField that tolerates lowercase string booleans from the
    encryption serializer and always returns a real Python bool.
    """
    def to_python(self, value):
        # If decryption gave a lowercase string, coerce before parent validation
        if isinstance(value, str):
            v = value.strip().lower()
            if v in _TRUTHY:
                return True
            if v in _FALSY:
                return False
        return super().to_python(value)

    def get_prep_value(self, value):
        # Ensure we never save a string back into the ciphertext
        if isinstance(value, str):
            v = value.strip().lower()
            if v in _TRUTHY:
                value = True
            elif v in _FALSY:
                value = False
        return super().get_prep_value(value)
