import base64
import json


def webauthn_encode(binary):
    return base64.urlsafe_b64encode(binary).decode('ascii').rstrip('=')


def webauthn_decode(text):
    text += '=' * (-len(text) % 4)
    return base64.urlsafe_b64decode(text)


class WebAuthnJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, bytes):
            return {'_bytes': webauthn_encode(o)}
        return super().default(o)
