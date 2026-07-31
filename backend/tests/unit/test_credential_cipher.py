from cryptography.fernet import Fernet

from app.core.security import CredentialCipher


def test_encrypt_decrypt_round_trip():
    cipher = CredentialCipher(key=Fernet.generate_key().decode())
    plaintext = "super-secret-password"
    ciphertext = cipher.encrypt(plaintext)
    assert ciphertext != plaintext
    assert cipher.decrypt(ciphertext) == plaintext


def test_different_keys_cannot_decrypt_each_others_ciphertext():
    cipher_a = CredentialCipher(key=Fernet.generate_key().decode())
    cipher_b = CredentialCipher(key=Fernet.generate_key().decode())
    ciphertext = cipher_a.encrypt("token-value")
    try:
        cipher_b.decrypt(ciphertext)
        assert False, "decrypting with the wrong key should raise"
    except Exception:
        pass
