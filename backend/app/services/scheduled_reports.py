"""
Scheduled Reports Service - Background job scheduling for automated email reports
"""
import logging
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler: Optional[AsyncIOScheduler] = None


def get_scheduler() -> AsyncIOScheduler:
    """Get or create the scheduler instance"""
    global scheduler
    if scheduler is None:
        scheduler = AsyncIOScheduler()
    return scheduler


def start_scheduler():
    """Start the scheduler if not already running"""
    global scheduler
    sched = get_scheduler()
    if not sched.running:
        sched.start()
        logger.info("Scheduler started")
        # Add the main check job that runs every hour
        sched.add_job(
            check_and_execute_schedules,
            CronTrigger(minute=0),  # Run at the top of every hour
            id='check_schedules',
            replace_existing=True
        )
        logger.info("Schedule check job added (runs hourly)")


def stop_scheduler():
    """Stop the scheduler"""
    global scheduler
    if scheduler and scheduler.running:
        scheduler.shutdown()
        logger.info("Scheduler stopped")


async def check_and_execute_schedules():
    """Check for schedules that need to be executed and run them"""
    from app.db.database import db
    from app.services.email_service import send_pdf_email, generate_summary_email_html, EmailDeliveryError
    from fpdf import FPDF
    
    logger.info("Checking scheduled reports...")
    
    now = datetime.now(timezone.utc)
    current_hour = now.hour
    current_day = now.weekday()  # 0=Monday, 6=Sunday
    current_date = now.day
    
    # Find active schedules
    schedules = await db.scheduled_reports.find({
        "is_active": True
    }).to_list(None)
    
    for schedule in schedules:
        try:
            should_run = False
            schedule_id = schedule.get("schedule_id")
            frequency = schedule.get("frequency")  # daily, weekly, monthly
            send_hour = schedule.get("send_hour", 9)  # Default 9 AM
            
            # Check if it's the right hour
            if current_hour != send_hour:
                continue
            
            # Check frequency conditions
            if frequency == "daily":
                should_run = True
            elif frequency == "weekly":
                send_day = schedule.get("send_day", 0)  # Default Monday
                should_run = (current_day == send_day)
            elif frequency == "monthly":
                send_date = schedule.get("send_date", 1)  # Default 1st of month
                should_run = (current_date == send_date)
            
            if not should_run:
                continue
            
            # Check last sent time to avoid duplicates
            last_sent = schedule.get("last_sent")
            if last_sent:
                hours_since_last = (now - last_sent).total_seconds() / 3600
                if hours_since_last < 20:  # Don't send if sent within last 20 hours
                    continue
            
            logger.info(f"Executing scheduled report: {schedule_id}")
            
            # Get user info
            user_id = schedule.get("user_id")
            user = await db.users.find_one({"user_id": user_id}, {"_id": 0})
            if not user:
                logger.warning(f"User {user_id} not found for schedule {schedule_id}")
                continue
            
            user_name = user.get("name", user.get("email", "JUSTICE User"))
            
            # Determine date range based on frequency
            if frequency == "daily":
                start_date = now - timedelta(days=1)
                period_label = "Daily"
            elif frequency == "weekly":
                start_date = now - timedelta(days=7)
                period_label = "Weekly"
            else:  # monthly
                start_date = now - timedelta(days=30)
                period_label = "Monthly"
            
            # Find recordings with summaries in the date range
            recordings_data = []
            recordings = await db.call_recordings.find({
                "participants": user_id,
                "ai_summary": {"$exists": True, "$ne": None},
                "started_at": {"$gte": start_date}
            }, {"_id": 0}).to_list(100)
            
            for recording in recordings:
                call = await db.video_calls.find_one(
                    {"call_id": recording.get("call_id")}, 
                    {"_id": 0}
                )
                recordings_data.append({
                    "recording": recording,
                    "call": call,
                    "summary": recording.get("ai_summary")
                })
            
            if not recordings_data:
                logger.info(f"No recordings with summaries found for schedule {schedule_id}")
                # Update last_sent anyway to prevent repeated checks
                await db.scheduled_reports.update_one(
                    {"schedule_id": schedule_id},
                    {"$set": {"last_sent": now, "last_result": "no_recordings"}}
                )
                continue
            
            # Generate PDF
            pdf = generate_scheduled_report_pdf(recordings_data, period_label, user_name)
            pdf_bytes = bytes(pdf.output())
            pdf_filename = f"{period_label.lower()}_summary_report_{now.strftime('%Y%m%d')}.pdf"
            
            # Generate email HTML
            recipients = schedule.get("recipient_emails", [])
            email_html = generate_scheduled_report_email_html(
                recording_count=len(recordings_data),
                period_label=period_label,
                sender_name=user_name,
                start_date=start_date,
                end_date=now
            )
            
            # Send email
            try:
                subject = f"{period_label} Call Summary Report - JUSTICE Platform"
                
                await send_pdf_email(
                    to_emails=recipients,
                    subject=subject,
                    body_html=email_html,
                    pdf_bytes=pdf_bytes,
                    pdf_filename=pdf_filename,
                    sender_name=user_name
                )
                
                # Update schedule with success
                await db.scheduled_reports.update_one(
                    {"schedule_id": schedule_id},
                    {"$set": {
                        "last_sent": now,
                        "last_result": "success",
                        "last_recording_count": len(recordings_data)
                    }}
                )
                
                logger.info(f"Scheduled report {schedule_id} sent successfully to {recipients}")
                
            except EmailDeliveryError as e:
                logger.error(f"Failed to send scheduled report {schedule_id}: {e}")
                await db.scheduled_reports.update_one(
                    {"schedule_id": schedule_id},
                    {"$set": {
                        "last_sent": now,
                        "last_result": f"failed: {str(e)}"
                    }}
                )
                
        except Exception as e:
            logger.error(f"Error processing schedule {schedule.get('schedule_id')}: {e}")


def generate_scheduled_report_pdf(recordings_data: list, period_label: str, user_name: str):
    """Generate PDF for scheduled report"""
    from fpdf import FPDF
    from datetime import datetime, timezone
    
    class ScheduledReportPDF(FPDF):
        def header(self):
            self.set_font('Helvetica', 'B', 16)
            self.set_text_color(79, 70, 229)
            self.cell(0, 10, 'JUSTICE PLATFORM', 0, 1, 'C')
            self.set_font('Helvetica', 'B', 14)
            self.set_text_color(0)
            self.cell(0, 8, f'{period_label} Consultation Summary Report', 0, 1, 'C')
            self.set_font('Helvetica', 'I', 10)
            self.set_text_color(128)
            self.cell(0, 5, f'Generated: {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}', 0, 1, 'C')
            self.set_text_color(0)
            self.line(10, 38, 200, 38)
            self.ln(12)
        
        def footer(self):
            self.set_y(-15)
            self.set_font('Helvetica', 'I', 8)
            self.set_text_color(128)
            self.cell(0, 10, f'Page {self.page_no()} | {period_label} Report for {user_name}', 0, 0, 'C')
    
    pdf = ScheduledReportPDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    
    # Summary page
    pdf.add_page()
    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_fill_color(79, 70, 229)
    pdf.set_text_color(255)
    pdf.cell(0, 8, f'  REPORT SUMMARY: {len(recordings_data)} Consultation(s)', 0, 1, 'L', fill=True)
    pdf.set_text_color(0)
    pdf.ln(5)
    
    # List consultations
    for idx, data in enumerate(recordings_data, 1):
        recording = data["recording"]
        call = data["call"]
        
        caller = call.get("caller_name", "Unknown") if call else "Unknown"
        recipient = call.get("recipient_name", "Unknown") if call else "Unknown"
        started_at = recording.get("started_at")
        
        if started_at and hasattr(started_at, 'strftime'):
            date_str = started_at.strftime('%b %d, %Y')
        else:
            date_str = str(started_at)[:10] if started_at else "Unknown"
        
        pdf.set_font('Helvetica', '', 10)
        pdf.cell(0, 6, f'{idx}. {caller} & {recipient} - {date_str}', 0, 1)
    
    # Individual summaries
    for idx, data in enumerate(recordings_data, 1):
        pdf.add_page()
        
        recording = data["recording"]
        call = data["call"]
        summary = data["summary"]
        
        caller = call.get("caller_name", "Unknown") if call else "Unknown"
        recipient = call.get("recipient_name", "Unknown") if call else "Unknown"
        
        pdf.set_font('Helvetica', 'B', 12)
        pdf.set_fill_color(59, 130, 246)
        pdf.set_text_color(255)
        pdf.cell(0, 8, f'  Consultation #{idx}: {caller} & {recipient}', 0, 1, 'L', fill=True)
        pdf.set_text_color(0)
        pdf.ln(3)
        
        # Render summary
        for line in summary.split('\n'):
            if pdf.get_y() > 260:
                pdf.add_page()
            
            clean_line = line.strip()
            if not clean_line:
                pdf.ln(2)
                continue
            
            if '**' in clean_line:
                section = clean_line.replace('**', '')
                if clean_line[0].isdigit():
                    parts = section.split('. ', 1)
                    section = parts[1] if len(parts) > 1 else section
                pdf.ln(2)
                pdf.set_font('Helvetica', 'B', 10)
                pdf.set_fill_color(79, 70, 229)
                pdf.set_text_color(255)
                pdf.cell(0, 6, f'  {section.upper()}', 0, 1, 'L', fill=True)
                pdf.set_text_color(0)
                continue
            
            if clean_line.startswith('-') or clean_line.startswith('•'):
                content = clean_line[1:].strip()
                pdf.set_font('Helvetica', '', 9)
                pdf.cell(5, 4, '', 0, 0)
                pdf.cell(5, 4, chr(149), 0, 0)
                pdf.multi_cell(0, 4, content)
                continue
            
            pdf.set_font('Helvetica', '', 9)
            pdf.multi_cell(0, 4, clean_line)
    
    return pdf


def generate_scheduled_report_email_html(
    recording_count: int,
    period_label: str,
    sender_name: str,
    start_date: datetime,
    end_date: datetime
):
    """Generate HTML email for scheduled report"""
    
    date_range = f"{start_date.strftime('%b %d')} - {end_date.strftime('%b %d, %Y')}"
    
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
            <h2 style="color: #1f2937; margin-bottom: 20px;">
                📊 Your {period_label} Summary Report
            </h2>
            
            <p style="font-size: 16px; margin-bottom: 20px;">
                Here's your automated {period_label.lower()} consultation summary report from the JUSTICE platform.
            </p>
            
            <div style="background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%); color: white; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <h3 style="margin: 0 0 15px 0; font-size: 18px;">📎 Report Details</h3>
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td style="padding: 5px 0; color: rgba(255,255,255,0.8);">Period:</td>
                        <td style="padding: 5px 0; font-weight: bold;">{date_range}</td>
                    </tr>
                    <tr>
                        <td style="padding: 5px 0; color: rgba(255,255,255,0.8);">Consultations:</td>
                        <td style="padding: 5px 0; font-weight: bold;">{recording_count}</td>
                    </tr>
                    <tr>
                        <td style="padding: 5px 0; color: rgba(255,255,255,0.8);">Generated for:</td>
                        <td style="padding: 5px 0; font-weight: bold;">{sender_name}</td>
                    </tr>
                </table>
            </div>
            
            <p style="font-size: 14px; color: #6b7280; margin-top: 30px;">
                The attached PDF contains AI-generated summaries of all your legal consultations 
                from the specified period, including key discussion points, action items, and legal considerations.
            </p>
            
            <p style="font-size: 14px; color: #6b7280;">
                To manage your scheduled reports, log into the JUSTICE platform and visit the Recordings page.
            </p>
        </div>
        
        <!-- Footer -->
        <div style="border-top: 1px solid #e5e7eb; padding-top: 20px; margin-top: 30px;">
            <p style="font-size: 12px; color: #9ca3af; margin: 0;">
                <strong>Confidentiality Notice:</strong> This email and any attachments are confidential. 
                If you are not the intended recipient, please delete this message.
            </p>
            <p style="font-size: 12px; color: #9ca3af; margin: 15px 0 0 0;">
                This is an automated report from JUSTICE Platform | Civil Rights Defense System
            </p>
        </div>
        
    </body>
    </html>
    """
    
    return html_content
