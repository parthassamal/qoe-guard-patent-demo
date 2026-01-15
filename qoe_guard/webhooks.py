"""
QoE-Guard Webhook Notifications

Send validation results to Slack, Discord, Microsoft Teams, or custom webhooks.
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional
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
    # Slack
    if slack_url := os.getenv("QOE_GUARD_SLACK_WEBHOOK"):
        send_webhook(slack_url, result, WebhookType.SLACK)
    
    # Discord
    if discord_url := os.getenv("QOE_GUARD_DISCORD_WEBHOOK"):
        send_webhook(discord_url, result, WebhookType.DISCORD)
    
    # Teams
    if teams_url := os.getenv("QOE_GUARD_TEAMS_WEBHOOK"):
        send_webhook(teams_url, result, WebhookType.TEAMS)
    
    # Custom
    if custom_url := os.getenv("QOE_GUARD_CUSTOM_WEBHOOK"):
        send_webhook(custom_url, result, WebhookType.CUSTOM)
