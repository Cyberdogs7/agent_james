from datetime import datetime
from tzlocal import get_localzone

def get_local_time():
    """Returns the current time in the local timezone."""
    return datetime.now(get_localzone())

def format_datetime(dt_object, time_format="12h"):
    """Formats a datetime object into a string including the date."""
    date_str = dt_object.strftime("%A, %B %d, %Y")
    if time_format == "12h":
        time_str = dt_object.strftime("%I:%M %p")
    else:
        time_str = dt_object.strftime("%H:%M")
    return f"{date_str} at {time_str}"

set_time_format_tool = {
    "name": "set_time_format",
    "description": "Sets the preferred time format for displaying time.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "format": {
                "type": "STRING",
                "description": "The desired time format, either '12h' or '24h'."
            }
        },
        "required": ["format"]
    }
}

get_datetime_tool = {
    "name": "get_datetime",
    "description": "Gets the current date and time in the local timezone.",
    "parameters": {
        "type": "OBJECT",
        "properties": {}
    }
}
