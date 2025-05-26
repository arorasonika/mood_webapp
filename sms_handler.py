from twilio.rest import Client
from config import Config # Imports configuration values (Twilio SID, Token, Number)
import phonenumbers # For phone number validation and formatting

def get_twilio_client():
    """Initializes and returns a Twilio Client instance."""
    # Create client on demand. For high-volume apps, initialize once at app startup.
    if not Config.TWILIO_ACCOUNT_SID or not Config.TWILIO_AUTH_TOKEN:
        print("Error: Twilio Account SID or Auth Token is not configured.")
        return None
    return Client(Config.TWILIO_ACCOUNT_SID, Config.TWILIO_AUTH_TOKEN)

def format_phone_to_e164(phone_number_str, country_code="US"):
    """
    Validates and formats a phone number string to E.164 standard (e.g., +14155552671).
    Uses 'US' as the default region hint if the number isn't already international.
    """
    if not phone_number_str:
        return None
    try:
        # If number already starts with '+', assume it's E.164 or close to it.
        if phone_number_str.startswith('+'):
            parsed_number = phonenumbers.parse(phone_number_str, None)
        else: # Otherwise, parse with a default region hint (e.g., "US").
            parsed_number = phonenumbers.parse(phone_number_str, country_code)

        if phonenumbers.is_valid_number(parsed_number):
            return phonenumbers.format_number(parsed_number, phonenumbers.PhoneNumberFormat.E164)
        else:
            print(f"Debug: Phone number '{phone_number_str}' (parsed as '{parsed_number}') is not valid.")
            return None
    except phonenumbers.phonenumberutil.NumberParseException as e:
        print(f"Error parsing phone number '{phone_number_str}': {e}")
        return None

def send_sms(to_phone_number_e164, body_text):
    """
    Sends an SMS message.
    'to_phone_number_e164' must be in E.164 format.
    """
    if not Config.TWILIO_PHONE_NUMBER:
        print("Error: Twilio Phone Number (sender) is not configured. SMS not sent.")
        return False

    twilio_client = get_twilio_client()
    if not twilio_client: # If client initialization failed
        return False

    if not to_phone_number_e164:
        print("Error: Invalid 'to' phone number for SMS (must be E.164). SMS not sent.")
        return False

    try:
        message = twilio_client.messages.create(
            body=body_text,
            from_=Config.TWILIO_PHONE_NUMBER, # Your Twilio phone number
            to=to_phone_number_e164          # Recipient's phone number
        )
        print(f"SMS sent to {to_phone_number_e164}: SID {message.sid}")
        return True
    except Exception as e:
        # Log the full error from Twilio for debugging.
        print(f"Error sending SMS to {to_phone_number_e164} from {Config.TWILIO_PHONE_NUMBER}: {e}")
        return False

def send_otp_sms(phone_number_e164, otp):
    """Sends the OTP verification code via SMS."""
    return send_sms(phone_number_e164, f"Your Mood Tracker verification code is: {otp}")

def send_daily_mood_prompt_sms(phone_number_e164):
    """Sends the daily mood prompt SMS."""
    print("sent sms")
    return send_sms(phone_number_e164, "How do you feel today? Reply with an emoji and optional text.")