# sensd/fields.py
from encrypted_fields.fields import EncryptedBooleanField

_TRUTHY = {"1","true","t","yes","y","on","True","TRUE"}
_FALSY  = {"0","false","f","no","n","off","","False","FALSE"}

class CoercedEncryptedBooleanField(EncryptedBooleanField):
    """
    Harden EncryptedBooleanField so that:
      - False/None never become NULL in DB
      - lowercase 'true'/'false' round-trip correctly
    """
    def to_python(self, value):
        # When decrypt returns strings like "false"/"true"
        print("Value in to_python:", value, type(value))
        if isinstance(value, str):
            v = value.strip().lower()
            if v in _TRUTHY: return True
            if v in _FALSY:  return False
        if value is None:
            return False
        return super().to_python(value)

    def get_prep_value(self, value):
        # Never allow None; coerce strings; force a definite bool token
        if value is None:
            value = False
        elif isinstance(value, str):
            v = value.strip().lower()
            if v in _TRUTHY: value = True
            elif v in _FALSY: value = False
        # Some backends treat falsy as empty → NULL; avoid by using explicit token
        return super().get_prep_value("True" if bool(value) else "False")

    # make migrations happy if this field appears in them
    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        path = "sensd.fields.CoercedEncryptedBooleanField"
        return name, path, args, kwargs
