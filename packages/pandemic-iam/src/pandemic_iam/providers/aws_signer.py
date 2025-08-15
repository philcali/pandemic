"""AWS IAM Roles Anywhere request signing implementation."""

import hashlib
import hmac
import json
from datetime import datetime
from typing import Any, Dict
from urllib.parse import quote

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding


class IAMRolesAnywhereSigner:
    """Signs requests for AWS IAM Roles Anywhere using X.509 certificates."""

    def __init__(self, certificate: x509.Certificate, private_key):
        self.certificate = certificate
        self.private_key = private_key
        self.service = "rolesanywhere"
        self.algorithm = "AWS4-X509-RSA-SHA256"

    def sign_request(
        self, method: str, url: str, headers: Dict[str, str], payload: str, region: str
    ) -> Dict[str, str]:
        """Sign AWS IAM Roles Anywhere request with X.509 certificate."""

        # Parse URL components
        from urllib.parse import urlparse

        parsed = urlparse(url)
        host = parsed.netloc
        path = parsed.path or "/"

        # Create timestamp
        timestamp = datetime.utcnow()
        amz_date = timestamp.strftime("%Y%m%dT%H%M%SZ")
        date_stamp = timestamp.strftime("%Y%m%d")

        # Add required headers
        headers = headers.copy()
        headers["Host"] = host
        headers["X-Amz-Date"] = amz_date
        headers["X-Amz-X509"] = self._get_certificate_header()

        # Create canonical request
        canonical_request = self._create_canonical_request(method, path, "", headers, payload)

        # Create string to sign
        credential_scope = f"{date_stamp}/{region}/{self.service}/aws4_request"
        string_to_sign = f"{self.algorithm}\n{amz_date}\n{credential_scope}\n{hashlib.sha256(canonical_request.encode()).hexdigest()}"

        # Sign with private key
        signature = self._sign_string(string_to_sign)

        # Create authorization header
        signed_headers = ";".join(sorted(headers.keys()))
        authorization = f"{self.algorithm} Credential=X509Certificate/{credential_scope}, SignedHeaders={signed_headers}, Signature={signature}"

        headers["Authorization"] = authorization
        return headers

    def _get_certificate_header(self) -> str:
        """Get base64-encoded certificate for X-Amz-X509 header."""
        import base64

        cert_der = self.certificate.public_bytes(serialization.Encoding.DER)
        return base64.b64encode(cert_der).decode()

    def _create_canonical_request(
        self, method: str, path: str, query_string: str, headers: Dict[str, str], payload: str
    ) -> str:
        """Create canonical request string."""

        # Canonical URI
        canonical_uri = quote(path, safe="/")

        # Canonical query string
        canonical_query_string = query_string

        # Canonical headers
        canonical_headers = ""
        for key in sorted(headers.keys()):
            canonical_headers += f"{key.lower()}:{headers[key].strip()}\n"

        # Signed headers
        signed_headers = ";".join(sorted(k.lower() for k in headers.keys()))

        # Payload hash
        payload_hash = hashlib.sha256(payload.encode()).hexdigest()

        return f"{method}\n{canonical_uri}\n{canonical_query_string}\n{canonical_headers}\n{signed_headers}\n{payload_hash}"

    def _sign_string(self, string_to_sign: str) -> str:
        """Sign string using private key."""
        signature_bytes = self.private_key.sign(
            string_to_sign.encode(), padding.PKCS1v15(), hashes.SHA256()
        )

        import base64

        return base64.b64encode(signature_bytes).hexdigest()
