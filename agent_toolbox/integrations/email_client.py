"""Email client integration for sending and receiving emails."""

import smtplib
import imaplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import Dict, List, Optional, Union, Any
import os


class EmailClient:
    """Email client for SMTP and IMAP operations."""
    
    def __init__(self, smtp_server: str, smtp_port: int, imap_server: str, imap_port: int,
                 username: str, password: str, use_tls: bool = True):
        """Initialize email client with server configuration."""
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.imap_server = imap_server
        self.imap_port = imap_port
        self.username = username
        self.password = password
        self.use_tls = use_tls
        
    def send_email(self, to_addresses: Union[str, List[str]], subject: str,
                   body: str, from_address: Optional[str] = None,
                   cc_addresses: Optional[List[str]] = None,
                   bcc_addresses: Optional[List[str]] = None,
                   attachments: Optional[List[str]] = None,
                   is_html: bool = False) -> Dict[str, Any]:
        """Send an email with optional attachments."""
        
        if from_address is None:
            from_address = self.username
            
        # Create message
        msg = MIMEMultipart()
        msg['From'] = from_address
        msg['To'] = to_addresses if isinstance(to_addresses, str) else ', '.join(to_addresses)
        msg['Subject'] = subject
        
        if cc_addresses:
            msg['Cc'] = ', '.join(cc_addresses)
            
        # Add body
        body_type = 'html' if is_html else 'plain'
        msg.attach(MIMEText(body, body_type))
        
        # Add attachments
        if attachments:
            for file_path in attachments:
                if os.path.exists(file_path):
                    with open(file_path, 'rb') as attachment:
                        part = MIMEBase('application', 'octet-stream')
                        part.set_payload(attachment.read())
                        
                    encoders.encode_base64(part)
                    part.add_header(
                        'Content-Disposition',
                        f'attachment; filename= {os.path.basename(file_path)}'
                    )
                    msg.attach(part)
                    
        try:
            # Connect to server and send
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls()
                server.login(self.username, self.password)
                
                # Prepare recipient list
                recipients = []
                if isinstance(to_addresses, str):
                    recipients.append(to_addresses)
                else:
                    recipients.extend(to_addresses)
                    
                if cc_addresses:
                    recipients.extend(cc_addresses)
                if bcc_addresses:
                    recipients.extend(bcc_addresses)
                    
                server.send_message(msg, to_addrs=recipients)
                
            return {"success": True, "message": "Email sent successfully"}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
            
    def get_emails(self, folder: str = 'INBOX', limit: int = 10,
                   search_criteria: str = 'ALL') -> List[Dict[str, Any]]:
        """Retrieve emails from specified folder."""
        
        emails = []
        
        try:
            # Connect to IMAP server
            with imaplib.IMAP4_SSL(self.imap_server, self.imap_port) as mail:
                mail.login(self.username, self.password)
                mail.select(folder)
                
                # Search for messages
                status, message_ids = mail.search(None, search_criteria)
                
                if status == 'OK':
                    # Get the most recent emails
                    message_list = message_ids[0].split()
                    recent_messages = message_list[-limit:] if len(message_list) > limit else message_list
                    
                    for msg_id in recent_messages:
                        status, msg_data = mail.fetch(msg_id, '(RFC822)')
                        
                        if status == 'OK':
                            email_body = msg_data[0][1]
                            email_message = email.message_from_bytes(email_body)
                            
                            # Extract email information
                            email_info = {
                                'id': msg_id.decode(),
                                'subject': email_message.get('Subject', ''),
                                'from': email_message.get('From', ''),
                                'to': email_message.get('To', ''),
                                'date': email_message.get('Date', ''),
                                'body': self._extract_body(email_message)
                            }
                            
                            emails.append(email_info)
                            
        except Exception as e:
            raise Exception(f"Failed to retrieve emails: {str(e)}")
            
        return emails
        
    def _extract_body(self, email_message) -> str:
        """Extract body text from email message."""
        body = ""
        
        if email_message.is_multipart():
            for part in email_message.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition"))
                
                if content_type == "text/plain" and "attachment" not in content_disposition:
                    body = part.get_payload(decode=True).decode()
                    break
        else:
            body = email_message.get_payload(decode=True).decode()
            
        return body