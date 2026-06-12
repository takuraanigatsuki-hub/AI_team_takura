"""Stripe Checkout — оплата подписок."""

from __future__ import annotations

import os
import hmac
import hashlib
import json
from typing import Optional

import httpx

from room.subscriptions import SUBSCRIPTION_PLANS, set_subscription_tier, add_balance

STRIPE_API = "https://api.stripe.com/v1"

TIER_PRICE_ENV = {
    "starter": "STRIPE_PRICE_STARTER",
    "pro": "STRIPE_PRICE_PRO",
    "team": "STRIPE_PRICE_TEAM",
}


def _secret_key() -> str:
    import config as cfg
    return (os.environ.get("STRIPE_SECRET_KEY") or cfg.config.get("stripe_secret_key") or "").strip()


def _webhook_secret() -> str:
    import config as cfg
    return (os.environ.get("STRIPE_WEBHOOK_SECRET") or cfg.config.get("stripe_webhook_secret") or "").strip()


def is_configured() -> bool:
    return bool(_secret_key())


def _price_id(tier: str) -> str:
    import config as cfg
    env_key = TIER_PRICE_ENV.get(tier, "")
    if env_key:
        pid = os.environ.get(env_key) or cfg.config.get(env_key.lower(), "")
        if pid:
            return pid.strip()
    return (cfg.config.get(f"stripe_price_{tier}") or "").strip()


def status() -> dict:
    return {
        "configured": is_configured(),
        "tiers": {
            t: bool(_price_id(t))
            for t in ("starter", "pro", "team")
        },
    }


async def create_checkout_session(
    *,
    user_id: str,
    user_email: str,
    tier: str,
    success_url: str,
    cancel_url: str,
) -> dict:
    if tier not in SUBSCRIPTION_PLANS or tier in ("free", "owner"):
        raise ValueError("Недоступный тариф")
    price = _price_id(tier)
    if not price:
        raise ValueError(f"Stripe price не настроен для {tier}. Укажите STRIPE_PRICE_{tier.upper()} в .env")
    key = _secret_key()
    if not key:
        raise ValueError("STRIPE_SECRET_KEY не задан")

    plan = SUBSCRIPTION_PLANS[tier]
    data = {
        "mode": "subscription",
        "success_url": success_url + ("&" if "?" in success_url else "?") + "billing=success",
        "cancel_url": cancel_url + ("&" if "?" in cancel_url else "?") + "billing=cancel",
        "customer_email": user_email,
        "client_reference_id": user_id,
        "line_items[0][price]": price,
        "line_items[0][quantity]": "1",
        "metadata[tier]": tier,
        "metadata[user_id]": user_id,
        "subscription_data[metadata][tier]": tier,
        "subscription_data[metadata][user_id]": user_id,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{STRIPE_API}/checkout/sessions",
            data=data,
            auth=(key, ""),
        )
        if resp.status_code >= 400:
            err = resp.json().get("error", {}).get("message", resp.text)
            raise RuntimeError(err)
        return resp.json()


def verify_webhook(payload: bytes, sig_header: str) -> bool:
    secret = _webhook_secret()
    if not secret:
        return False
    parts = {}
    for item in sig_header.split(","):
        k, _, v = item.partition("=")
        parts[k.strip()] = v.strip()
    ts = parts.get("t", "")
    v1 = parts.get("v1", "")
    if not ts or not v1:
        return False
    signed = f"{ts}.{payload.decode('utf-8')}"
    expected = hmac.new(secret.encode(), signed.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, v1)


def handle_webhook_event(event: dict, *, users_loader, users_saver) -> dict:
    """Обработка checkout.session.completed и invoice.paid."""
    etype = event.get("type", "")
    obj = event.get("data", {}).get("object", {})

    if etype == "checkout.session.completed":
        user_id = obj.get("client_reference_id") or obj.get("metadata", {}).get("user_id", "")
        tier = obj.get("metadata", {}).get("tier", "starter")
        if user_id and tier in SUBSCRIPTION_PLANS and tier not in ("free", "owner"):
            set_subscription_tier(user_id, tier, users_loader=users_loader, users_saver=users_saver)
            plan = SUBSCRIPTION_PLANS[tier]
            add_balance(user_id, plan.get("monthly_credits", 0), users_loader=users_loader, users_saver=users_saver)
            return {"ok": True, "action": "subscription_activated", "tier": tier, "user_id": user_id}

    if etype == "invoice.paid":
        sub_meta = obj.get("subscription_details", {}).get("metadata") or obj.get("lines", {}).get("data", [{}])[0].get("metadata", {})
        user_id = sub_meta.get("user_id", "")
        tier = sub_meta.get("tier", "")
        if user_id and tier:
            plan = SUBSCRIPTION_PLANS.get(tier, {})
            credits = plan.get("monthly_credits", 0)
            if credits:
                add_balance(user_id, credits, users_loader=users_loader, users_saver=users_saver)
            return {"ok": True, "action": "credits_renewed", "user_id": user_id}

    return {"ok": True, "action": "ignored", "type": etype}
