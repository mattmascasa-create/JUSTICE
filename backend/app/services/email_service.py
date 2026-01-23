"""
Email Service - SendGrid integration for sending emails with attachments
"""
import os
import base64
import logging
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Attachment, FileContent, FileName, FileType, Disposition

logger = logging.getLogger(__name__)

class EmailDeliveryError(Exception):
    pass


def get_sendgrid_client():
    """Get SendGrid client with API key from environment"""
    api_key = os.environ.get("SENDGRID_API_KEY")
    if not api_key:
        raise EmailDeliveryError("SendGrid API key not configured. Please set SENDGRID_API_KEY in environment.")
    return SendGridAPIClient(api_key)


def get_sender_email():
    """Get verified sender email from environment"""
    sender = os.environ.get("SENDGRID_SENDER_EMAIL", os.environ.get("SENDER_EMAIL"))
    if not sender:
        raise EmailDeliveryError("Sender email not configured. Please set SENDGRID_SENDER_EMAIL in environment.")
    return sender


async def send_pdf_email(
    to_emails: list,
    subject: str,
    body_html: str,
    pdf_bytes: bytes,
    pdf_filename: str,
    cc_emails: list = None,
    sender_name: str = "JUSTICE Platform"
):
    """
    Send an email with PDF attachment via SendGrid
    
    Args:
        to_emails: List of recipient email addresses
        subject: Email subject line
        body_html: HTML content of the email body
        pdf_bytes: PDF file content as bytes
        pdf_filename: Name for the PDF attachment
        cc_emails: Optional list of CC email addresses
        sender_name: Display name for the sender
    
    Returns:
        dict with status and details
    """
    try:
        sg = get_sendgrid_client()
        sender_email = get_sender_email()
        
        # Create the email message
        message = Mail(
            from_email=(sender_email, sender_name),
            to_emails=to_emails,
            subject=subject,
            html_content=body_html
        )
        
        # Add CC recipients if provided
        if cc_emails:
            for cc in cc_emails:
                message.add_cc(cc)
        
        # Encode PDF and create attachment
        encoded_pdf = base64.b64encode(pdf_bytes).decode()
        
        attachment = Attachment()
        attachment.file_content = FileContent(encoded_pdf)
        attachment.file_name = FileName(pdf_filename)
        attachment.file_type = FileType("application/pdf")
        attachment.disposition = Disposition("attachment")
        
        message.add_attachment(attachment)
        
        # Send the email
        response = sg.send(message)
        
        if response.status_code in [200, 201, 202]:
            logger.info(f"Email sent successfully to {to_emails}")
            return {
                "status": "sent",
                "recipients": to_emails,
                "cc": cc_emails,
                "status_code": response.status_code
            }
        else:
            logger.error(f"SendGrid returned status {response.status_code}")
            raise EmailDeliveryError(f"SendGrid returned status {response.status_code}")
            
    except EmailDeliveryError:
        raise
    except Exception as e:
        logger.error(f"Email delivery failed: {str(e)}")
        raise EmailDeliveryError(f"Failed to send email: {str(e)}")


def generate_summary_email_html(
    recording_count: int,
    sender_name: str,
    recipient_name: str = None,
    custom_message: str = None
):
    """Generate HTML content for summary email"""
    
    greeting = f"Dear {recipient_name}," if recipient_name else "Hello,"
    
    custom_section = ""
    if custom_message:
        custom_section = f"""
        <div style="background-color: #f8f9fa; padding: 15px; border-radius: 8px; margin: 20px 0;">
            <p style="margin: 0; color: #333;">{custom_message}</p>
        </div>
        """
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
        
        <!-- Header -->
        <div style="text-align: center; padding: 20px 0; border-bottom: 2px solid #4f46e5;">
            <h1 style="color: #4f46e5; margin: 0; font-size: 28px;">JUSTICE</h1>
            <p style="color: #6b7280; margin: 5px 0 0 0; font-size: 14px;">Civil Rights Defense System</p>
        </div>
        
        <!-- Main Content -->
        <div style="padding: 30px 0;">
            <p style="font-size: 16px; margin-bottom: 20px;">{greeting}</p>
            
            <p style="font-size: 16px; margin-bottom: 20px;">
                <strong>{sender_name}</strong> has shared a consultation summary report with you from the JUSTICE platform.
            </p>
            
            {custom_section}
            
            <div style="background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%); color: white; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <h3 style="margin: 0 0 10px 0; font-size: 18px;">📎 Attached Document</h3>
                <p style="margin: 0; font-size: 14px;">
                    {"Consolidated Summary Report" if recording_count > 1 else "Call Summary Report"} 
                    ({recording_count} consultation{'' if recording_count == 1 else 's'})
                </p>
            </div>
            
            <p style="font-size: 14px; color: #6b7280; margin-top: 30px;">
                This report contains AI-generated summaries of legal consultations, including key discussion points, 
                action items, and legal considerations. Please review the attached PDF for detailed information.
            </p>
        </div>
        
        <!-- Footer -->
        <div style="border-top: 1px solid #e5e7eb; padding-top: 20px; margin-top: 30px;">
            <p style="font-size: 12px; color: #9ca3af; margin: 0;">
                <strong>Confidentiality Notice:</strong> This email and any attachments are confidential and may contain 
                legally privileged information. If you are not the intended recipient, please notify the sender 
                immediately and delete this message.
            </p>
            <p style="font-size: 12px; color: #9ca3af; margin: 15px 0 0 0;">
                Powered by JUSTICE Platform | Civil Rights Defense System
            </p>
        </div>
        
    </body>
    </html>
    """
    
    return html_content
