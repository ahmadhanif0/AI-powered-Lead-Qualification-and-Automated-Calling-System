import asyncio
import smtplib
import textwrap
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import settings
from app.logs.logger import logger


class NotificationService:

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    async def send_notification(self, lead: dict, decision: str):

        lead_id    = lead.get("id")
        name       = lead.get("name") or f"Lead #{lead_id}"
        phone      = lead.get("phone")    or "N/A"
        email_addr = lead.get("email")    or "N/A"
        company    = lead.get("company")  or "N/A"
        score      = lead.get("score",  0)
        transcript = lead.get("last_transcript") or ""

        # ── Console / log notification ──────────────────────────────
        sep = "=" * 60
        logger.info(sep)
        logger.info("🔔  SALES ALERT — ACTION REQUIRED")
        logger.info(f"   Decision  : {decision}")
        logger.info(f"   Lead ID   : {lead_id}")
        logger.info(f"   Name      : {name}")
        logger.info(f"   Company   : {company}")
        logger.info(f"   Email     : {email_addr}")
        logger.info(f"   Phone     : {phone}")
        logger.info(f"   Score     : {score}")
        logger.info(sep)

        # ── Email notification ──────────────────────────────────────
        if not settings.ENABLE_EMAIL_NOTIFICATIONS:
            return {"notified": True, "channel": "log", "lead_id": lead_id}

        if not all([
            settings.SMTP_USER,
            settings.SMTP_PASSWORD,
            settings.NOTIFICATION_EMAIL_FROM,
            settings.NOTIFICATION_EMAIL_TO,
        ]):
            logger.warning(
                "Email notifications enabled but SMTP credentials are "
                "incomplete — skipping email send."
            )
            return {"notified": True, "channel": "log", "lead_id": lead_id}

        # Build and send — retry once on failure
        for attempt in range(1, 3):
            try:
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    self._send_email,
                    lead_id, name, phone, email_addr,
                    company, score, transcript, decision
                )
                logger.info(
                    f"Email notification sent for lead {lead_id} "
                    f"(decision: {decision})"
                )
                return {
                    "notified": True,
                    "channel":  "email",
                    "lead_id":  lead_id
                }

            except Exception as e:
                logger.error(
                    f"Email send attempt {attempt} failed for lead "
                    f"{lead_id}: {e}"
                )
                if attempt < 2:
                    await asyncio.sleep(3)   # brief pause before retry

        # Both attempts failed — workflow continues regardless
        logger.error(
            f"All email attempts failed for lead {lead_id}. "
            "Workflow continues."
        )
        return {"notified": False, "channel": "email_failed", "lead_id": lead_id}

    # ------------------------------------------------------------------
    # Internal: synchronous SMTP send (run in executor to stay async)
    # ------------------------------------------------------------------

    def _send_email(
        self,
        lead_id:    int,
        name:       str,
        phone:      str,
        email_addr: str,
        company:    str,
        score:      float,
        transcript: str,
        decision:   str,
    ):
        recipients = [
            r.strip()
            for r in settings.NOTIFICATION_EMAIL_TO.split(",")
            if r.strip()
        ]

        subject = f"🔥 New {decision} Lead: {name}"

        # Trim transcript to first 500 chars for the email excerpt
        transcript_excerpt = (
            transcript[:500] + "…" if len(transcript) > 500 else transcript
        ) or "No transcript available."

        plain_body = textwrap.dedent(f"""
            AI LEAD QUALIFICATION ALERT
            ===========================

            Decision  : {decision}
            Lead ID   : {lead_id}
            Name      : {name}
            Company   : {company}
            Email     : {email_addr}
            Phone     : {phone}
            Score     : {score}

            TRANSCRIPT EXCERPT
            ------------------
            {transcript_excerpt}

            View full details: {settings.DASHBOARD_URL}

            ---
            Sent by {settings.APP_NAME}
        """).strip()

        html_body = f"""
        <html><body style="font-family:Arial,sans-serif;color:#333;max-width:600px">
          <h2 style="color:#16a34a">🔥 {decision} Lead Alert</h2>
          <table style="border-collapse:collapse;width:100%">
            <tr><td style="padding:6px;font-weight:bold;width:120px">Lead ID</td>
                <td style="padding:6px">{lead_id}</td></tr>
            <tr style="background:#f9f9f9">
                <td style="padding:6px;font-weight:bold">Name</td>
                <td style="padding:6px">{name}</td></tr>
            <tr><td style="padding:6px;font-weight:bold">Company</td>
                <td style="padding:6px">{company}</td></tr>
            <tr style="background:#f9f9f9">
                <td style="padding:6px;font-weight:bold">Email</td>
                <td style="padding:6px">{email_addr}</td></tr>
            <tr><td style="padding:6px;font-weight:bold">Phone</td>
                <td style="padding:6px">{phone}</td></tr>
            <tr style="background:#f9f9f9">
                <td style="padding:6px;font-weight:bold">Score</td>
                <td style="padding:6px"><strong>{score}</strong></td></tr>
            <tr><td style="padding:6px;font-weight:bold">Decision</td>
                <td style="padding:6px;color:#16a34a;font-weight:bold">{decision}</td></tr>
          </table>

          <h3 style="margin-top:24px">Transcript Excerpt</h3>
          <pre style="background:#f4f4f4;padding:12px;border-radius:4px;
                      white-space:pre-wrap;font-size:13px">{transcript_excerpt}</pre>

          <p style="margin-top:24px">
            <a href="{settings.DASHBOARD_URL}"
               style="background:#2563eb;color:white;padding:10px 20px;
                      border-radius:4px;text-decoration:none">
              View Dashboard →
            </a>
          </p>

          <hr style="margin-top:32px;border:none;border-top:1px solid #eee"/>
          <p style="font-size:11px;color:#999">Sent by {settings.APP_NAME}</p>
        </body></html>
        """

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = settings.NOTIFICATION_EMAIL_FROM
        msg["To"]      = ", ".join(recipients)

        msg.attach(MIMEText(plain_body, "plain"))
        msg.attach(MIMEText(html_body,  "html"))

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(
                settings.NOTIFICATION_EMAIL_FROM,
                recipients,
                msg.as_string()
            )
