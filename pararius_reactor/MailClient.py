import imaplib
import email
import socket


class MailClient:
    """Handles Gmail IMAP fetching (IPv4 forced)"""

    def __init__(self, server, email_account, password, mailbox="INBOX"):
        self.server = server
        self.email_account = email_account
        self.password = password
        self.mailbox = mailbox

    def _connect(self):
        """Force IPv4 connection to IMAP server"""
        # Resolve IPv4 address explicitly
        addr_info = socket.getaddrinfo(
            self.server, 993, socket.AF_INET, socket.SOCK_STREAM
        )
        ipv4_addr = addr_info[0][4][0]  # grab the IP string
        # Connect using the resolved IPv4
        mail = imaplib.IMAP4_SSL(ipv4_addr, 993)
        # still use server name for login (Google checks creds, not host)
        mail.login(self.email_account, self.password)
        mail.select(self.mailbox)
        return mail

    def fetch_unseen_from(self, sender):
        """Fetch unseen messages from specific sender"""
        try:
            mail = self._connect()
        except Exception as e:
            print(f"[MailClient] Connection failed: {e}")
            return []

        status, data = mail.search(None, f'(UNSEEN FROM "{sender}")')
        if status != "OK":
            mail.logout()
            return []

        messages = []
        for num in data[0].split():
            try:
                status, msg_data = mail.fetch(num, "(RFC822)")
                if status != "OK":
                    continue
                raw_email = msg_data[0][1]
                msg = email.message_from_bytes(raw_email)
                messages.append((num, msg))
            except Exception as e:
                print(f"[MailClient] Error fetching {num}: {e}")
                continue

        mail.logout()
        return messages
