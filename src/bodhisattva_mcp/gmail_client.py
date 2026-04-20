"""Gmail client: Protocol + real Google implementation + in-memory fake.

OAuth for the real client uses the installed-application device flow.
Credentials are cached at ``~/.bodhisattva/credentials.json``. The only
Gmail scope requested is ``gmail.send`` — principle of least privilege.
"""

from __future__ import annotations

import base64
import logging
from dataclasses import dataclass, field
from email.mime.text import MIMEText
from pathlib import Path
from typing import Protocol

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]


class GmailAuthError(Exception):
    """Raised when OAuth fails or credentials are invalid/expired."""


class GmailSendError(Exception):
    """Raised when the Gmail API rejects a send."""


@dataclass(frozen=True)
class EmailToSend:
    to: str
    subject: str
    body: str

    def __post_init__(self) -> None:
        if not self.to:
            raise ValueError("to must not be empty")
        if "@" not in self.to:
            raise ValueError(f"to must be an email address, got: {self.to!r}")


class GmailClient(Protocol):
    def send(self, email: EmailToSend) -> str:
        """Send ``email``. Return the Gmail message id on success."""


@dataclass
class FakeGmailClient:
    """Test double: records sends, optionally raises a configured error."""

    fail_with: Exception | None = None
    sent: list[EmailToSend] = field(default_factory=list)
    _counter: int = 0

    def send(self, email: EmailToSend) -> str:
        if self.fail_with is not None:
            raise self.fail_with
        self.sent.append(email)
        self._counter += 1
        return f"fake-{self._counter}"


class GoogleGmailClient:
    """Real Gmail client. Lazy-imports the Google SDK."""

    def __init__(self, credentials_path: Path, client_secret_path: Path) -> None:
        self._creds_path = credentials_path
        self._client_secret_path = client_secret_path
        self._service = None  # Built lazily.

    def _build_service(self):  # pragma: no cover — exercised by manual tests
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build

        creds: Credentials | None = None
        if self._creds_path.exists():
            creds = Credentials.from_authorized_user_file(str(self._creds_path), SCOPES)

        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as exc:  # noqa: BLE001
                raise GmailAuthError(f"credentials refresh failed: {exc}") from exc

        if not creds or not creds.valid:
            if not self._client_secret_path.exists():
                raise GmailAuthError(
                    f"client secret not found at {self._client_secret_path}"
                )
            flow = InstalledAppFlow.from_client_secrets_file(
                str(self._client_secret_path), SCOPES
            )
            creds = flow.run_local_server(port=0)
            self._creds_path.parent.mkdir(parents=True, exist_ok=True)
            self._creds_path.write_text(creds.to_json())
            self._creds_path.chmod(0o600)

        return build("gmail", "v1", credentials=creds, cache_discovery=False)

    def send(self, email: EmailToSend) -> str:  # pragma: no cover
        if self._service is None:
            self._service = self._build_service()

        message = MIMEText(email.body)
        message["to"] = email.to
        message["subject"] = email.subject
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

        try:
            sent = (
                self._service.users()
                .messages()
                .send(userId="me", body={"raw": raw})
                .execute()
            )
        except Exception as exc:  # noqa: BLE001
            raise GmailSendError(f"Gmail send failed: {exc}") from exc

        return str(sent["id"])
