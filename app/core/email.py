from typing import Protocol

import httpx

from app.core.config import get_settings

settings = get_settings()


class EmailSender(Protocol):
    async def send(self, to: str, subject: str, body: str) -> None: ...


class ConsoleSender:
    async def send(self, to: str, subject: str, body: str) -> None:
        print(f"\n=== EMAIL ===\nTo: {to}\nSubject: {subject}\n\n{body}\n=============\n")


class ResendSender:
    async def send(self, to: str, subject: str, body: str) -> None:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {settings.resend_api_key}"},
                json={
                    "from": settings.email_from,
                    "to": [to],
                    "subject": subject,
                    "text": body,
                },
            )

        if response.is_error:
            raise RuntimeError(
                f"Resend rejected the email ({response.status_code}): {response.text}"
            )


def get_sender() -> EmailSender:
    """Return the real sender when an API key is configured, otherwise print to stdout.

    Local development and tests have no key, so they never send real email.
    """
    if settings.resend_api_key:
        return ResendSender()
    return ConsoleSender()
