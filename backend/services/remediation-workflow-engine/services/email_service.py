import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Any
import logging
import os

logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        self.smtp_host = os.getenv("SMTP_HOST", "localhost")
        self.smtp_port = int(os.getenv("SMTP_PORT", "1025"))  # MailHog for development
        self.smtp_username = os.getenv("SMTP_USERNAME", "")
        self.smtp_password = os.getenv("SMTP_PASSWORD", "")
        self.from_email = os.getenv("FROM_EMAIL", "compliance@juliusbaer.com")
    
    async def send_email(self, to_emails: List[str], subject: str, body: str, cc_emails: List[str] = None) -> Dict[str, Any]:
        """Send email using SMTP"""
        
        try:
            # Create message
            message = MIMEMultipart()
            message["From"] = self.from_email
            message["To"] = ", ".join(to_emails)
            message["Subject"] = subject
            
            if cc_emails:
                message["Cc"] = ", ".join(cc_emails)
            
            # Add body
            message.attach(MIMEText(body, "html" if "<html>" in body else "plain"))
            
            # Send email
            async with aiosmtplib.AsyncSMTP(hostname=self.smtp_host, port=self.smtp_port) as smtp:
                if self.smtp_username and self.smtp_password:
                    await smtp.login(self.smtp_username, self.smtp_password)
                
                recipients = to_emails + (cc_emails or [])
                await smtp.send_message(message)
            
            logger.info(f"Email sent successfully to {to_emails}")
            return {
                "success": True,
                "message": "Email sent successfully",
                "recipients": recipients
            }
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return {
                "success": False,
                "error": str(e),
                "recipients": to_emails
            }
    
    async def send_edd_request(self, to_email: str, subject: str, body: str, cc_email: str = None) -> Dict[str, Any]:
        """Send Enhanced Due Diligence document request"""
        
        # For development, we'll log instead of actually sending
        logger.info(f"EDD Request Email:")
        logger.info(f"To: {to_email}")
        logger.info(f"Subject: {subject}")
        logger.info(f"Body: {body}")
        
        if cc_email:
            logger.info(f"CC: {cc_email}")
        
        # In production, uncomment the following line:
        # return await self.send_email([to_email], subject, body, [cc_email] if cc_email else [])
        
        return {
            "success": True,
            "message": "EDD request logged (development mode)",
            "recipients": [to_email]
        }
    
    async def send_escalation_notification(self, workflow_instance_id: str, escalation_reason: str, to_roles: List[str]) -> Dict[str, Any]:
        """Send escalation notification"""
        
        subject = f"AML Workflow Escalation - {workflow_instance_id}"
        body = f"""
        <html>
        <body>
            <h2>AML Workflow Escalation Notification</h2>
            <p><strong>Workflow Instance:</strong> {workflow_instance_id}</p>
            <p><strong>Escalation Reason:</strong> {escalation_reason}</p>
            <p><strong>Required Action:</strong> Please review the workflow in the AML system.</p>
            <p><strong>Timestamp:</strong> {__import__('datetime').datetime.now().isoformat()}</p>
            <br>
            <p>Best regards,<br>AML Compliance System</p>
        </body>
        </html>
        """
        
        # In a real system, you would lookup emails based on roles
        to_emails = ["compliance_team@juliusbaer.com"]  # Example
        
        return await self.send_email(to_emails, subject, body)