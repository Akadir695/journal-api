from typing import Protocol


class EmailSender(Protocol):
    async def send(self, to: str, subject: str, body: str) -> None: ...


class ConsoleSender:
    async def send(self, to: str, subject: str, body: str) -> None:
        print(f"\n=== EMAIL ===\nTo: {to}\nSubject: {subject}\n\n{body}\n=============\n")


def get_sender() -> EmailSender:
    return ConsoleSender()
