from fastapi import APIRouter, Request, Form
from fastapi.responses import PlainTextResponse
from twilio.twiml.messaging_response import MessagingResponse
from sqlalchemy.orm import Session
from App.database.db import SessionLocal
from App.database.models import Order, CustomerRegistry
from App.services.db_service import get_registered_customer, register_customer
from datetime import datetime, timezone, timedelta
import re
import os
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()

IST = timezone(timedelta(hours=5, minutes=30))

# ─── In-memory registration state ───────────────────────────────────────────
# Structure: { phone_number: { "state": "awaiting_name"|"awaiting_location",
#                              "name": str,
#                              "pending_cans": int } }
registration_state = {}


# ─── Helpers ─────────────────────────────────────────────────────────────────

def get_next_customer_id(db: Session) -> str:
    """Auto-generate next customer ID: C1, C2, C3..."""
    last = db.query(CustomerRegistry).order_by(
        CustomerRegistry.id.desc()
    ).first()
    if not last or not last.customer_id:
        return "C1"
    # Extract number from "C5" → 5, increment to 6
    try:
        num = int(last.customer_id.replace("C", ""))
        return f"C{num + 1}"
    except ValueError:
        return "C1"


def parse_cans(message: str) -> int:
    """Extract number of cans from message. Returns 0 if not found."""
    message = message.lower().strip()
    word_map = {
        "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
        "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10
    }
    for word, num in word_map.items():
        if word in message:
            return num
    numbers = re.findall(r'\d+', message)
    if numbers:
        return int(numbers[0])
    return 0


def save_order(db: Session, phone_number: str, num_cans: int, customer_name: str = None) -> Order:
    """Save a confirmed order to DB and return it."""
    order = Order(
        created_at=datetime.now(IST),
        phone_number=phone_number,
        customer_name=customer_name,
        num_cans=num_cans,
        status="pending",
        delivery_date=datetime.now(IST).strftime("%Y-%m-%d")
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


# ─── Main Webhook ─────────────────────────────────────────────────────────────

@router.post("/whatsapp-webhook")
async def whatsapp_webhook(
    request: Request,
    From: str = Form(...),
    Body: str = Form(default=""),
    Latitude: str = Form(default=None),
    Longitude: str = Form(default=None),
):
    
    form_data = await request.form()
    print("=== ALL TWILIO FIELDS ===")
    for key, value in form_data.items():
        print(f"  {key}: {value}")
    print("========================")
    

    db = SessionLocal()
    resp = MessagingResponse()
    phone_number = From.replace("whatsapp:", "")
    message_body = Body.strip()

    print(f"\n📩 From: {phone_number} | Body: '{message_body}' | Lat: {Latitude} | Lon: {Longitude}")

    try:
        customer = get_registered_customer(db, phone_number)
        state = registration_state.get(phone_number, {})

        # ── CASE 1: Customer is mid-registration ──────────────────────────────
        if state.get("state") == "awaiting_name":
            # They've replied with their name
            name = message_body.strip()
            if not name or len(name) < 2:
                resp.message("Please enter your name (at least 2 characters).")
                return PlainTextResponse(str(resp), media_type="application/xml")

            # Save name, move to next state
            registration_state[phone_number]["name"] = name
            registration_state[phone_number]["state"] = "awaiting_location"

            resp.message(
                f"Nice to meet you, {name}! 👋\n\n"
                f"Now please share your location so we know where to deliver.\n\n"
                f"📍 Tap Attach → Location → Share Current Location"
            )
            return PlainTextResponse(str(resp), media_type="application/xml")

        if state.get("state") == "awaiting_location":
            # Check if they shared a location
            if Latitude and Longitude:
                lat = float(Latitude)
                lon = float(Longitude)
                name = state.get("name", "Customer")
                pending_cans = state.get("pending_cans", 0)

                # Generate customer ID and register
                customer_id = get_next_customer_id(db)
                register_customer(db, phone_number, name, lat, lon, customer_id)

                # Clear state
                del registration_state[phone_number]

                print(f"✅ Registered {name} as {customer_id} at ({lat}, {lon})")

                # If they had a pending order, place it now
                if pending_cans > 0:
                    order = save_order(db, phone_number, pending_cans, name)
                    resp.message(
                        f"✅ You're registered as {customer_id}!\n\n"
                        f"And your order is confirmed:\n"
                        f"🪣 Cans: {pending_cans}\n"
                        f"📅 Delivery: Tomorrow\n"
                        f"🔖 Order ID: #{order.id}\n\n"
                        f"Thank you, {name}! We'll deliver tomorrow."
                    )
                else:
                    resp.message(
                        f"✅ Registration complete! You're now {customer_id}.\n\n"
                        f"To place an order, just message us the number of cans.\n"
                        f"Example: '2 cans' or just '2'"
                    )
            else:
                # They sent text instead of location
                resp.message(
                    f"We need your location to register. 📍\n\n"
                    f"Please tap Attach → Location → Share Current Location\n\n"
                    f"(Don't type an address — use the location share button)"
                )
            return PlainTextResponse(str(resp), media_type="application/xml")

        # ── CASE 2: Registered customer — handle order ────────────────────────
        if customer:
            num_cans = parse_cans(message_body)

            if num_cans <= 0:
                resp.message(
                    f"Hi {customer.name}! 👋\n\n"
                    f"To place an order, reply with the number of cans.\n"
                    f"Example: '2 cans' or just '2'"
                )
            elif num_cans > 20:
                resp.message("Maximum 20 cans per order. Please reply with 1–20.")
            else:
                order = save_order(db, phone_number, num_cans, customer.name)
                resp.message(
                    f"Order confirmed! ✅\n\n"
                    f"👤 {customer.name} ({customer.customer_id})\n"
                    f"🪣 Cans: {num_cans}\n"
                    f"📅 Delivery: Tomorrow\n"
                    f"🔖 Order ID: #{order.id}\n\n"
                    f"Thank you!"
                )
            return PlainTextResponse(str(resp), media_type="application/xml")

        # ── CASE 3: Unknown customer — start registration ─────────────────────
        num_cans = parse_cans(message_body)
        pending_cans = num_cans if 0 < num_cans <= 20 else 0

        # Start registration flow
        registration_state[phone_number] = {
            "state": "awaiting_name",
            "pending_cans": pending_cans
        }

        if pending_cans > 0:
            resp.message(
                f"Welcome! 👋 We received your request for {pending_cans} can(s).\n\n"
                f"You're not registered yet — let's do that quickly!\n\n"
                f"What's your name?"
            )
        else:
            resp.message(
                f"Welcome! 👋 You're not registered yet.\n\n"
                f"Let's get you set up quickly!\n\n"
                f"What's your name?"
            )

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        resp.message("Sorry, something went wrong. Please try again.")

    finally:
        db.close()

    return PlainTextResponse(str(resp), media_type="application/xml")