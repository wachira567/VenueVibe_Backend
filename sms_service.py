import os
import africastalking
from typing import Optional


# Africa's Talking SMS Service
class SMSService:
    def __init__(self):
        # Initialize Africa's Talking
        username = os.getenv("AT_USERNAME", "VenueVibe")
        api_key = os.getenv("AT_API_KEY")

        if not api_key:
            print("Warning: AT_API_KEY not found. SMS functionality disabled.")
            self.sms = None
            return

        try:
            africastalking.initialize(username, api_key)
            self.sms = africastalking.SMS
            print("SMS service initialized successfully")
        except Exception as e:
            print(f"Failed to initialize SMS service: {e}")
            self.sms = None

    def send_sms(self, phone_number: str, message: str) -> bool:
        """
        Send SMS to a phone number
        Phone number should be in international format (e.g., +254XXXXXXXXX)
        """
        if not self.sms:
            print("SMS service not initialized")
            return False

        try:
            # Ensure phone number starts with +
            if not phone_number.startswith("+"):
                # Assume Kenyan number if no country code
                if phone_number.startswith("0"):
                    phone_number = "+254" + phone_number[1:]
                else:
                    phone_number = "+" + phone_number

            response = self.sms.send(message, [phone_number])
            print(f"SMS sent successfully to {phone_number}: {message}")
            return True

        except Exception as e:
            print(f"Failed to send SMS to {phone_number}: {e}")
            return False

    def send_booking_received_sms(
        self, phone_number: str, venue_name: str, event_date: str
    ) -> bool:
        """Send booking received notification"""
        message = f"VenueVibe: Booking received for {venue_name} on {event_date}. Status: Pending."
        return self.send_sms(phone_number, message)

    def send_booking_approved_sms(self, phone_number: str, venue_name: str) -> bool:
        """Send booking approved notification"""
        message = f"VenueVibe: GOOD NEWS! Your booking at {venue_name} is APPROVED."
        return self.send_sms(phone_number, message)

    def send_booking_rejected_sms(self, phone_number: str, venue_name: str) -> bool:
        """Send booking rejected notification"""
        message = f"VenueVibe: Your booking at {venue_name} was not approved. Contact us for alternatives."
        return self.send_sms(phone_number, message)

    def send_welcome_sms(self, phone_number: str, username: str) -> bool:
        """Send welcome message to new users"""
        message = f"Welcome to VenueVibe, {username}! 🎉 Discover amazing venues for your events."
        return self.send_sms(phone_number, message)

    def send_event_reminder_sms(
        self, phone_number: str, venue_name: str, event_date: str
    ) -> bool:
        """Send event reminder (day before event)"""
        message = f"VenueVibe: Reminder - Your event at {venue_name} is tomorrow ({event_date}). See you there! 🎊"
        return self.send_sms(phone_number, message)

    def send_payment_reminder_sms(
        self, phone_number: str, venue_name: str, amount: int
    ) -> bool:
        """Send payment reminder for unpaid bookings"""
        message = f"VenueVibe: Payment pending for {venue_name} - KES {amount:,}. Complete payment to confirm booking."
        return self.send_sms(phone_number, message)


# Global SMS service instance
sms_service = SMSService()
