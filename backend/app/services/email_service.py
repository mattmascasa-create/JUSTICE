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



def is_sendgrid_configured() -> bool:
    """Check if SendGrid is properly configured"""
    return bool(os.environ.get("SENDGRID_API_KEY"))


async def send_simple_email(
    to_email: str,
    subject: str,
    html_content: str,
    plain_content: str = None
) -> dict:
    """
    Send a simple email without attachments.
    
    Returns:
        dict with success status and any errors
    """
    if not is_sendgrid_configured():
        logger.warning("SendGrid not configured - Email not sent")
        return {
            "success": False,
            "error": "SendGrid not configured",
            "configured": False
        }
    
    try:
        sg = get_sendgrid_client()
        sender_email = get_sender_email()
        
        message = Mail(
            from_email=(sender_email, "JUSTICE Alerts"),
            to_emails=to_email,
            subject=subject,
            html_content=html_content
        )
        
        response = sg.send(message)
        success = response.status_code in [200, 201, 202]
        
        logger.info(f"Email sent to {to_email}: status={response.status_code}")
        
        return {
            "success": success,
            "status_code": response.status_code,
            "to": to_email
        }
        
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
        return {
            "success": False,
            "error": str(e),
            "to": to_email
        }


def generate_sos_alert_html(
    user_name: str,
    location_address: str,
    share_url: str,
    latitude: float = None,
    longitude: float = None
) -> str:
    """Generate HTML content for SOS alert email"""
    
    maps_link = ""
    if latitude and longitude:
        maps_link = f"""
        <p style="margin: 10px 0;">
            <a href="https://maps.google.com/?q={latitude},{longitude}" 
               style="background-color: #4285f4; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">
                📍 View Location on Map
            </a>
        </p>
        """
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="background: linear-gradient(135deg, #dc2626 0%, #991b1b 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
            <h1 style="color: white; margin: 0; font-size: 28px;">🚨 EMERGENCY SOS ALERT 🚨</h1>
        </div>
        
        <div style="background-color: #fef2f2; padding: 30px; border: 2px solid #dc2626; border-top: none; border-radius: 0 0 10px 10px;">
            <p style="font-size: 18px; margin-bottom: 20px;">
                <strong>{user_name}</strong> is in a police encounter and has triggered an emergency alert!
            </p>
            
            <div style="background-color: white; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #dc2626;">
                <h3 style="margin-top: 0; color: #dc2626;">📍 Location</h3>
                <p style="margin-bottom: 0;">{location_address}</p>
            </div>
            
            {maps_link}
            
            <div style="text-align: center; margin: 30px 0;">
                <a href="{share_url}" 
                   style="background-color: #dc2626; color: white; padding: 15px 40px; text-decoration: none; border-radius: 8px; font-size: 18px; font-weight: bold; display: inline-block;">
                    👁️ WATCH LIVE STREAM
                </a>
            </div>
            
            <p style="color: #666; font-size: 14px; margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd;">
                This is an automated emergency alert from <strong>JUSTICE</strong> - Civil Rights Defense System.
            </p>
        </div>
    </body>
    </html>
    """


def generate_dead_mans_switch_html(
    user_name: str,
    location_address: str,
    share_url: str,
    latitude: float = None,
    longitude: float = None
) -> str:
    """Generate HTML content for Dead Man's Switch alert email"""
    
    maps_link = ""
    if latitude and longitude:
        maps_link = f"""
        <p style="margin: 10px 0;">
            <a href="https://maps.google.com/?q={latitude},{longitude}" 
               style="background-color: #4285f4; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">
                📍 View Location on Map
            </a>
        </p>
        """
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="background: linear-gradient(135deg, #f97316 0%, #c2410c 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
            <h1 style="color: white; margin: 0; font-size: 28px;">⚠️ DEAD MAN'S SWITCH TRIGGERED ⚠️</h1>
        </div>
        
        <div style="background-color: #fff7ed; padding: 30px; border: 2px solid #f97316; border-top: none; border-radius: 0 0 10px 10px;">
            <p style="font-size: 18px; margin-bottom: 20px;">
                <strong>{user_name}</strong> has become <strong style="color: #c2410c;">UNRESPONSIVE</strong> during a police encounter!
            </p>
            
            <div style="background-color: #fef3c7; padding: 15px; border-radius: 8px; margin: 20px 0; border: 1px solid #f59e0b;">
                <p style="margin: 0; font-weight: bold; color: #92400e;">
                    ⚡ They may need immediate assistance. Please check on them!
                </p>
            </div>
            
            <div style="background-color: white; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #f97316;">
                <h3 style="margin-top: 0; color: #c2410c;">📍 Last Known Location</h3>
                <p style="margin-bottom: 0;">{location_address}</p>
            </div>
            
            {maps_link}
            
            <div style="text-align: center; margin: 30px 0;">
                <a href="{share_url}" 
                   style="background-color: #f97316; color: white; padding: 15px 40px; text-decoration: none; border-radius: 8px; font-size: 18px; font-weight: bold; display: inline-block;">
                    👁️ WATCH LIVE STREAM
                </a>
            </div>
            
            <p style="color: #666; font-size: 14px; margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd;">
                This automated alert was triggered because {user_name} did not respond to activity checks.
                <br><strong>JUSTICE</strong> - Civil Rights Defense System
            </p>
        </div>
    </body>
    </html>
    """


async def send_sos_alert_email(
    to_email: str,
    user_name: str,
    location_address: str,
    share_url: str,
    latitude: float = None,
    longitude: float = None
) -> dict:
    """Send an SOS alert email to an emergency contact."""
    
    subject = f"🚨 EMERGENCY SOS: {user_name} needs help!"
    html_content = generate_sos_alert_html(
        user_name=user_name,
        location_address=location_address,
        share_url=share_url,
        latitude=latitude,
        longitude=longitude
    )
    
    return await send_simple_email(to_email, subject, html_content)


async def send_dead_mans_switch_email(
    to_email: str,
    user_name: str,
    location_address: str,
    share_url: str,
    latitude: float = None,
    longitude: float = None
) -> dict:
    """Send a Dead Man's Switch alert email to an emergency contact."""
    
    subject = f"⚠️ URGENT: {user_name} is unresponsive during encounter!"
    html_content = generate_dead_mans_switch_html(
        user_name=user_name,
        location_address=location_address,
        share_url=share_url,
        latitude=latitude,
        longitude=longitude
    )
    
    return await send_simple_email(to_email, subject, html_content)


def generate_document_shared_html(
    sender_name: str,
    document_title: str,
    document_type: str,
    message: str = None,
    view_url: str = None
) -> str:
    """Generate HTML content for document shared notification email"""
    
    message_section = ""
    if message:
        message_section = f"""
        <div style="background-color: #f8fafc; padding: 15px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #3b82f6;">
            <p style="margin: 0; font-style: italic; color: #475569;">"{message}"</p>
            <p style="margin: 10px 0 0 0; font-size: 12px; color: #94a3b8;">— {sender_name}</p>
        </div>
        """
    
    view_button = ""
    if view_url:
        view_button = f"""
        <div style="text-align: center; margin: 30px 0;">
            <a href="{view_url}" 
               style="background-color: #3b82f6; color: white; padding: 14px 35px; text-decoration: none; border-radius: 8px; font-size: 16px; font-weight: 600; display: inline-block;">
                📄 View Document
            </a>
        </div>
        """
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif; line-height: 1.6; color: #1e293b; max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f1f5f9;">
        <div style="background-color: white; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);">
            <!-- Header -->
            <div style="background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%); padding: 30px; text-align: center;">
                <h1 style="color: white; margin: 0; font-size: 24px;">📄 Document Shared With You</h1>
            </div>
            
            <!-- Main Content -->
            <div style="padding: 30px;">
                <p style="font-size: 16px; margin-bottom: 20px;">
                    <strong>{sender_name}</strong> has shared a legal document with you on the JUSTICE platform.
                </p>
                
                <div style="background-color: #eff6ff; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <h3 style="margin: 0 0 10px 0; color: #1d4ed8; font-size: 18px;">📋 {document_title}</h3>
                    <p style="margin: 0; color: #64748b; font-size: 14px;">Type: {document_type.replace('_', ' ').title()}</p>
                </div>
                
                {message_section}
                
                {view_button}
                
                <p style="font-size: 14px; color: #64748b; margin-top: 30px; padding-top: 20px; border-top: 1px solid #e2e8f0;">
                    Log in to your JUSTICE account to view and respond to this document. 
                    This document may contain important legal information regarding a civil rights matter.
                </p>
            </div>
            
            <!-- Footer -->
            <div style="background-color: #f8fafc; padding: 20px 30px; border-top: 1px solid #e2e8f0;">
                <p style="font-size: 12px; color: #94a3b8; margin: 0;">
                    <strong>Confidentiality Notice:</strong> This email and any linked documents may contain confidential 
                    and legally privileged information. If you are not the intended recipient, please notify us immediately.
                </p>
                <p style="font-size: 12px; color: #94a3b8; margin: 15px 0 0 0;">
                    <strong>JUSTICE</strong> — Civil Rights Defense System
                </p>
            </div>
        </div>
    </body>
    </html>
    """


async def send_document_shared_email(
    to_email: str,
    sender_name: str,
    document_title: str,
    document_type: str,
    message: str = None,
    view_url: str = None
) -> dict:
    """Send a notification email when a document is shared."""
    
    subject = f"📄 {sender_name} shared a document with you"
    html_content = generate_document_shared_html(
        sender_name=sender_name,
        document_title=document_title,
        document_type=document_type,
        message=message,
        view_url=view_url
    )
    
    return await send_simple_email(to_email, subject, html_content)
