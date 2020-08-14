import base64
from email.utils import formatdate
from Crypto.Hash import SHA256
from httpsig.utils import HttpSigException
from requests.auth import AuthBase
from httpsig.requests_auth import HTTPSignatureAuth


class StrateosSign(AuthBase):
    """Signs requests"""

    def __init__(self, email, secret):
        self.email = email
        self.secret = secret
        headers = ["(request-target)", "Date", "Host"]
        body_headers = ["Digest", "Content-Length"]
        try:
            self.auth = HTTPSignatureAuth(
                key_id=self.email,
                algorithm="rsa-sha256",
                headers=headers,
                secret=self.secret,
            )
            self.body_auth = HTTPSignatureAuth(
                key_id=self.email,
                algorithm="rsa-sha256",
                headers=headers + body_headers,
                secret=self.secret,
            )
        except HttpSigException:
            raise ValueError(
                "Could not parse the specified RSA Key, ensure it "
                "is a PRIVATE key in PEM format"
            )

    def __call__(self, request):
        if "Date" not in request.headers:
            request.headers["Date"] = formatdate(
                timeval=None, localtime=False, usegmt=True
            )

        if request.method.upper() in ("PUT", "POST", "PATCH"):
            digest = SHA256.new(request.body.encode()).digest()
            sha = base64.b64encode(digest).decode("ascii")
            request.headers["Digest"] = f"SHA-256={sha}"
            return self.body_auth(request)

        return self.auth(request)
