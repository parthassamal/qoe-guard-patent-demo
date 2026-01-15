"""
QoE-Guard Webhook Notifications

Send validation results to Slack, Gmail, Discord, Microsoft Teams, or custom webhooks.
"""
from __future__ import annotations

import json
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

import requests


class WebhookType(Enum):
    SLACK = "slack"
    DISCORD = "discord"
    TEAMS = "teams"
    CUSTOM = "custom"


@dataclass
class ValidationResult:
    run_id: str
    endpoint: str
    risk_score: float
    action: str  # PASS/WARN/FAIL
    change_count: int
    top_signals: list
    report_url: Optional[str] = None


def get_color(action: str) -> str:
    """Get color code based on decision."""
    return {
        "PASS": "#22c55e",  # green
        "WARN": "#eab308",  # yellow
        "FAIL": "#ef4444",  # red
    }.get(action, "#6b7280")


def get_emoji(action: str) -> str:
    """Get emoji based on decision."""
    return {
        "PASS": "✅",
        "WARN": "⚠️",
        "FAIL": "🚨",
    }.get(action, "❓")


def format_slack(result: ValidationResult) -> Dict[str, Any]:
    """Format for Slack webhook."""
    emoji = get_emoji(result.action)
    color = get_color(result.action)
    
    signals_text = "\n".join(
        f"• {s['signal']}: {s['value']}"
        for s in result.top_signals[:4]
    )
    
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"{emoji} QoE-Guard: {result.action}",
            }
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Endpoint:*\n`{result.endpoint}`"},
                {"type": "mrkdwn", "text": f"*Risk Score:*\n{result.risk_score:.4f}"},
                {"type": "mrkdwn", "text": f"*Changes:*\n{result.change_count}"},
                {"type": "mrkdwn", "text": f"*Run ID:*\n`{result.run_id[:8]}...`"},
            ]
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Top Signals:*\n{signals_text}"
            }
        },
    ]
    
    if result.report_url:
        blocks.append({
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "View Report"},
                    "url": result.report_url,
                    "style": "primary" if result.action == "PASS" else "danger"
                }
            ]
        })
    
    return {
        "attachments": [{"color": color, "blocks": blocks}]
    }


def format_discord(result: ValidationResult) -> Dict[str, Any]:
    """Format for Discord webhook."""
    emoji = get_emoji(result.action)
    color = int(get_color(result.action).replace("#", ""), 16)
    
    return {
        "embeds": [{
            "title": f"{emoji} QoE-Guard: {result.action}",
            "color": color,
            "fields": [
                {"name": "Endpoint", "value": f"`{result.endpoint}`", "inline": True},
                {"name": "Risk Score", "value": f"{result.risk_score:.4f}", "inline": True},
                {"name": "Changes", "value": str(result.change_count), "inline": True},
                {
                    "name": "Top Signals",
                    "value": "\n".join(f"• {s['signal']}: {s['value']}" for s in result.top_signals[:4]),
                    "inline": False
                },
            ],
            "url": result.report_url,
        }]
    }


def format_teams(result: ValidationResult) -> Dict[str, Any]:
    """Format for Microsoft Teams webhook."""
    emoji = get_emoji(result.action)
    color = get_color(result.action)
    
    facts = [
        {"name": "Endpoint", "value": result.endpoint},
        {"name": "Risk Score", "value": f"{result.risk_score:.4f}"},
        {"name": "Changes", "value": str(result.change_count)},
    ]
    
    for s in result.top_signals[:4]:
        facts.append({"name": s["signal"], "value": str(s["value"])})
    
    card = {
        "@type": "MessageCard",
        "@context": "http://schema.org/extensions",
        "themeColor": color.replace("#", ""),
        "summary": f"QoE-Guard: {result.action}",
        "sections": [{
            "activityTitle": f"{emoji} QoE-Guard Validation: {result.action}",
            "facts": facts,
            "markdown": True
        }]
    }
    
    if result.report_url:
        card["potentialAction"] = [{
            "@type": "OpenUri",
            "name": "View Report",
            "targets": [{"os": "default", "uri": result.report_url}]
        }]
    
    return card


def format_email_html(result: ValidationResult) -> str:
    """Format validation result as HTML email."""
    emoji = get_emoji(result.action)
    color = get_color(result.action)
    
    signals_html = "".join(
        f"<li><strong>{s['signal']}:</strong> {s['value']}</li>"
        for s in result.top_signals[:4]
    )
    
    report_link = f'<a href="{result.report_url}" style="background-color: {color}; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block; margin-top: 15px;">View Full Report</a>' if result.report_url else ""
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background-color: {color}; color: white; padding: 20px; border-radius: 5px 5px 0 0; }}
            .content {{ background-color: #f9f9f9; padding: 20px; border-radius: 0 0 5px 5px; }}
            .metric {{ display: inline-block; margin: 10px 20px 10px 0; }}
            .metric-label {{ font-size: 12px; color: #666; text-transform: uppercase; }}
            .metric-value {{ font-size: 24px; font-weight: bold; color: {color}; }}
            ul {{ list-style: none; padding: 0; }}
            li {{ padding: 5px 0; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>{emoji} QoE-Guard Validation: {result.action}</h1>
            </div>
            <div class="content">
                <div class="metric">
                    <div class="metric-label">Risk Score</div>
                    <div class="metric-value">{result.risk_score:.4f}</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Changes Detected</div>
                    <div class="metric-value">{result.change_count}</div>
                </div>
                
                <h3>Endpoint</h3>
                <p><code>{result.endpoint}</code></p>
                
                <h3>Top Signals</h3>
                <ul>{signals_html}</ul>
                
                <p><strong>Run ID:</strong> <code>{result.run_id}</code></p>
                
                {report_link}
            </div>
        </div>
    </body>
    </html>
    """


def format_email_text(result: ValidationResult) -> str:
    """Format validation result as plain text email."""
    emoji = get_emoji(result.action)
    signals_text = "\n".join(f"  • {s['signal']}: {s['value']}" for s in result.top_signals[:4])
    report_link = f"\nView report: {result.report_url}" if result.report_url else ""
    
    return f"""
{emoji} QoE-Guard Validation: {result.action}

Endpoint:     {result.endpoint}
Risk Score:   {result.risk_score:.4f}
Changes:      {result.change_count}
Run ID:       {result.run_id}

Top Signals:
{signals_text}
{report_link}
"""


def send_email(
    smtp_server: str,
    smtp_port: int,
    sender_email: str,
    sender_password: str,
    recipient_emails: List[str],
    result: ValidationResult,
    subject_prefix: str = "QoE-Guard",
    use_tls: bool = True,
) -> bool:
    """Send validation result via email (Gmail or SMTP)."""
    try:
        emoji = get_emoji(result.action)
        subject = f"{emoji} {subject_prefix}: {result.action} - {result.endpoint}"
        
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = sender_email
        msg["To"] = ", ".join(recipient_emails)
        
        # Plain text version
        text_part = MIMEText(format_email_text(result), "plain")
        msg.attach(text_part)
        
        # HTML version
        html_part = MIMEText(format_email_html(result), "html")
        msg.attach(html_part)
        
        # Send email
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            if use_tls:
                server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
        
        return True
        
    except Exception as e:
        print(f"Email error: {e}")
        return False


def send_gmail(
    sender_email: str,
    app_password: str,
    recipient_emails: List[str],
    result: ValidationResult,
) -> bool:
    """Send email via Gmail SMTP."""
    return send_email(
        smtp_server="smtp.gmail.com",
        smtp_port=587,
        sender_email=sender_email,
        sender_password=app_password,
        recipient_emails=recipient_emails,
        result=result,
        subject_prefix="QoE-Guard",
        use_tls=True,
    )


def send_webhook(
    webhook_url: str,
    result: ValidationResult,
    webhook_type: WebhookType = WebhookType.SLACK,
    timeout: int = 10,
) -> bool:
    """Send validation result to webhook."""
    try:
        if webhook_type == WebhookType.SLACK:
            payload = format_slack(result)
        elif webhook_type == WebhookType.DISCORD:
            payload = format_discord(result)
        elif webhook_type == WebhookType.TEAMS:
            payload = format_teams(result)
        else:
            # Custom: send raw result
            payload = {
                "run_id": result.run_id,
                "endpoint": result.endpoint,
                "risk_score": result.risk_score,
                "action": result.action,
                "change_count": result.change_count,
                "top_signals": result.top_signals,
                "report_url": result.report_url,
            }
        
        resp = requests.post(
            webhook_url,
            json=payload,
            timeout=timeout,
            headers={"Content-Type": "application/json"}
        )
        resp.raise_for_status()
        return True
        
    except Exception as e:
        print(f"Webhook error: {e}")
        return False


def notify_from_env(result: ValidationResult) -> None:
    """Send notifications based on environment variables."""
    # Slack (priority: high visibility)
    if slack_url := os.getenv("QOE_GUARD_SLACK_WEBHOOK"):
        send_webhook(slack_url, result, WebhookType.SLACK)
    
    # Gmail/Email (priority: high visibility)
    if gmail_user := os.getenv("QOE_GUARD_GMAIL_USER"):
        gmail_password = os.getenv("QOE_GUARD_GMAIL_APP_PASSWORD")
        recipients = os.getenv("QOE_GUARD_EMAIL_RECIPIENTS", "").split(",")
        recipients = [r.strip() for r in recipients if r.strip()]
        
        if gmail_password and recipients:
            send_gmail(
                sender_email=gmail_user,
                app_password=gmail_password,
                recipient_emails=recipients,
                result=result,
            )
    
    # Discord
    if discord_url := os.getenv("QOE_GUARD_DISCORD_WEBHOOK"):
        send_webhook(discord_url, result, WebhookType.DISCORD)
    
    # Teams
    if teams_url := os.getenv("QOE_GUARD_TEAMS_WEBHOOK"):
        send_webhook(teams_url, result, WebhookType.TEAMS)
    
    # Custom
    if custom_url := os.getenv("QOE_GUARD_CUSTOM_WEBHOOK"):
        send_webhook(custom_url, result, WebhookType.CUSTOM)
