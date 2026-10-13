"""Fixtures for the Ingress integration."""

import pytest


@pytest.fixture(autouse=True)
def custom_integrations(enable_custom_integrations):
    """Allow Home Assistant to load the integration under test."""


@pytest.fixture(scope="session")
def tls_certificates():
    """Generate local certificates with valid, wrong-host, and expired identities."""
    from datetime import datetime, timedelta, timezone
    from ipaddress import ip_address

    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID

    now = datetime.now(timezone.utc)
    ca_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    server_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    ca_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Ingress test CA")])

    def certificate(host, *, ca=False, expired=False, self_signed=False):
        key = ca_key if ca else server_key
        subject = ca_name if ca else x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, host)])
        signing_key = key if self_signed or ca else ca_key
        builder = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(subject if self_signed or ca else ca_name)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - timedelta(days=3))
            .not_valid_after(now + timedelta(days=30) if not expired else now - timedelta(days=1))
            .add_extension(x509.BasicConstraints(ca=ca, path_length=None), critical=True)
            .add_extension(x509.SubjectKeyIdentifier.from_public_key(key.public_key()), critical=False)
            .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(signing_key.public_key()), critical=False)
            .add_extension(x509.KeyUsage(
                digital_signature=True, content_commitment=False, key_encipherment=not ca,
                data_encipherment=False, key_agreement=False, key_cert_sign=ca,
                crl_sign=ca, encipher_only=False, decipher_only=False,
            ), critical=True)
        )
        if not ca:
            names = [x509.DNSName(host)]
            if host == "localhost":
                names.append(x509.IPAddress(ip_address("127.0.0.1")))
            builder = builder.add_extension(x509.SubjectAlternativeName(names), critical=False)
        return builder.sign(signing_key, hashes.SHA256()).public_bytes(serialization.Encoding.PEM).decode()

    return {
        "ca": certificate("", ca=True),
        "valid": certificate("localhost"),
        "wrong_host": certificate("another.example"),
        "expired": certificate("localhost", expired=True),
        "self_signed": certificate("localhost", self_signed=True),
        "key": server_key.private_bytes(
            serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        ).decode(),
    }
