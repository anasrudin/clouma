"""Tests for AES-256-GCM secret encryption helpers."""
import pytest
from agent_runtime.crypto import encrypt_value, decrypt_value

HEX_KEY = "a" * 64  # 32-byte key — valid for AES-256


def test_encrypt_decrypt_roundtrip():
    plaintext = "my-secret-token-123"
    ciphertext = encrypt_value(plaintext, HEX_KEY)
    assert ciphertext != plaintext
    assert decrypt_value(ciphertext, HEX_KEY) == plaintext


def test_encrypted_value_has_prefix():
    result = encrypt_value("hello", HEX_KEY)
    assert result.startswith("enc:")


def test_different_encryptions_produce_different_output():
    """Nonce is random — same plaintext yields different ciphertext each time."""
    a = encrypt_value("same", HEX_KEY)
    b = encrypt_value("same", HEX_KEY)
    assert a != b  # different nonces


def test_no_key_returns_plaintext():
    assert encrypt_value("plain", "") == "plain"
    assert decrypt_value("plain", "") == "plain"


def test_decrypt_without_prefix_returns_as_is():
    """Plaintext stored before encryption was enabled is returned unchanged."""
    assert decrypt_value("old-plaintext-value", HEX_KEY) == "old-plaintext-value"


def test_decrypt_with_no_key_returns_as_is():
    encrypted = encrypt_value("secret", HEX_KEY)
    # If key is lost/not set, value is returned as-is (encrypted blob)
    assert decrypt_value(encrypted, "") == encrypted
