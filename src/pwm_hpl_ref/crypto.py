import base64
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from .canonical import canonical_json

def generate_keypair():
    private = Ed25519PrivateKey.generate()
    return private, private.public_key()

def sign_json(private_key: Ed25519PrivateKey, value) -> str:
    return base64.b64encode(private_key.sign(canonical_json(value))).decode("ascii")

def verify_json(public_key: Ed25519PublicKey, value, signature: str) -> bool:
    try:
        public_key.verify(base64.b64decode(signature), canonical_json(value))
        return True
    except Exception:
        return False
