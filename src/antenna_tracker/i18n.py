"""UI strings.

The module language stays English until ``app.main()`` calls ``set_language``.
Unknown language codes fall back to Hebrew. Missing catalog keys fall back to
the English source.
"""

from __future__ import annotations

_LANGUAGE = "en"

# English source -> Hebrew. Units and acronyms (QR, GPS, USB, UTM, GET) stay Latin.
_HE: dict[str, str] = {
    "Antenna Tracker": "עוקב אנטנה",
    "Tracker settings": "הגדרות עוקב",
    "Fine-tune calibration and QR capture. Hardware and location are managed by setup.": (
        "כיול וקליטת QR. חומרה ומיקום נקבעים בהגדרה."
    ),
    "COMPASS CALIBRATION": "כיול מצפן",
    "Magnetic declination": "נטייה מגנטית",
    "Applied only when the alignment direction was measured with a compass.": (
        "חל רק כשהכיוון נמדד במצפן."
    ),
    "QR CAPTURE REGION": "אזור קליטת QR",
    "Frame width": "רוחב פריים",
    "Frame height": "גובה פריים",
    "Fraction of the video frame scanned from the top-left corner (0.05\u20131.00).": (
        "חלק מהפריים שנסרק מהפינה השמאלית-עליונה (\u20660.05\u20131.00\u2069)."
    ),
    "Run setup again": "הרץ הגדרה מחדש",
    "Save": "שמירה",
    "Cancel": "ביטול",
    "Language": "שפה",
    "Finish": "סיום",
    "SIM ALTITUDE": "גובה סימולציה",
    "Orbit site": "הקפה סביב האתר",
    "AUTO": "אוטומטי",
    "MANUAL": "ידני",
    "Drone": "רחפן",
    "Altitude": "גובה",
    "Heading": "כיוון",
    "Home distance": "מרחק לבית",
    "QR rate": "קצב QR",
    "Height \u2014   Home \u2014   Heading \u2014": "גובה \u2014   בית \u2014   כיוון \u2014",
    "AZIMUTH": "אזימוט",
    "ELEVATION": "הגבהה",
    "MANUAL CONTROL": "שליטה ידנית",
    "ANTENNA TRACKER": "עוקב אנטנה",
    "\u25cf LIVE": "\u25cf חי",
    "DRONE LINK": "קישור רחפן",
    "POINTING SOLUTION": "פתרון כיוון",
    "SIMULATION & DEVELOPER": "סימולציה ומפתח",
    "Power OFF": "כיבוי מתח",
    "Power ON": "הפעלת מתח",
    "Drone position: Video QR": "מיקום רחפן: QR מווידאו",
    "Drone position: Simulated": "מיקום רחפן: מדומה",
    "QR LINK ACTIVE": "קישור QR פעיל",
    "NO QR CODE DETECTED": "לא זוהה קוד QR",
    "Height {height} m   Home {home}   Heading {heading}": (
        "גובה {height} m   בית {home}   כיוון {heading}"
    ),
    "DRONE HAS NO GPS \u2013 aim the antenna manually": "אין GPS לרחפן \u2013 כוונו את האנטנה ידנית",
    "Drone GPS is back": "ה-GPS של הרחפן חזר",
    "POSSIBLE JAMMING \u2013 aim the antenna manually": "חשד לשיבוש \u2013 כוונו את האנטנה ידנית",
    "TRACKING": "במעקב",
    "OUT OF RANGE": "מחוץ לטווח",
    "NO DRONE POSITION": "אין מיקום רחפן",
    "NO FRESH DRONE POSITION": "אין מיקום עדכני",
    "NO POWER": "אין מתח",
    "NO DRONE GPS": "אין GPS לרחפן",
    "Silence alarm": "השתק אזעקה",
    "Reconnects automatically": "מתחבר מחדש לבד",
    "POWER LOST": "אובדן מתח",
    "Tracker has no power": "אין מתח לעוקב",
    "Check the battery and power cable.\nThe app will reconnect by itself.": (
        "בדקו סוללה וכבל מתח.\nהמערכת תתחבר מחדש לבד."
    ),
    "POWER RESTORED": "המתח חזר",
    "Tracker is back": "העוקב חזר",
    "Tracking resumes automatically.": "המעקב מתחדש לבד.",
    "Point to target": "כוון למטרה",
    "Arrow keys nudge 1\u00b0 \u00b7 hold to repeat": "מקשי החצים מזיזים \u20661\u00b0\u2069 \u00b7 החזקה לחזרה",
    "The tracker cannot move further this way": "העוקב לא יכול לזוז יותר בכיוון זה",
    "Setup": "הגדרה",
    "Continue": "המשך",
    "Back": "חזרה",
    "Align the tracker": "יישור העוקב",
    "Set the center direction carefully; the turret can rotate about 85\u00b0 to either side.": (
        "קבעו את כיוון המרכז בזהירות; הצריח מסתובב כ-\u206685\u00b0\u2069 לכל צד."
    ),
    "Center tracker": "מרכז עוקב",
    "Direction measured with": "הכיוון נמדד עם",
    "Map": "מפה",
    "Compass": "מצפן",
    "CENTER  \u2192  AIM  \u2192  CONFIRM": "\u2066מרכז  \u2192  כיוון  \u2192  אישור\u2069",
    (
        "<b>1</b> &nbsp; Center the turret using the button below.<br><br>"
        "<b>2</b> &nbsp; Rotate the entire base toward a known direction, ideally the flight area.<br><br>"
        "<b>3</b> &nbsp; Enter that direction (0\u00b0 north, 90\u00b0 east)."
    ): (
        "<b>\u20661\u2069</b> &nbsp; מרכזו את הצריח בכפתור למטה.<br><br>"
        "<b>\u20662\u2069</b> &nbsp; סובבו את הבסיס לכיוון ידוע, רצוי אזור הטיסה.<br><br>"
        "<b>\u20663\u2069</b> &nbsp; הזינו את הכיוון (\u20660\u00b0\u2069 צפון, \u206690\u00b0\u2069 מזרח)."
    ),
    "Center direction": "כיוון מרכז",
    "PHYSICAL ALIGNMENT": "יישור פיזי",
    "REFERENCE DIRECTION": "כיוון ייחוס",
    "\u2714 Map \u2014 true north.": "\u2714 מפה \u2014 צפון אמיתי.",
    "\u2714 Compass \u2014 magnetic north.": "\u2714 מצפן \u2014 צפון מגנטי.",
    "Start tracking": "התחל מעקב",
    "Sent reset... waiting for the tracker": "איפוס נשלח... ממתין לעוקב",
    "\u2714 Tracker is at its middle position.": "\u2714 העוקב במיקום המרכז.",
    "Connect your equipment": "חיבור הציוד",
    "Select the tracker and receiver video, then verify the hardware link.": (
        "בחרו עוקב ווידאו מקלט, ואז בדקו את הקישור."
    ),
    "\u21bb Refresh": "\u21bb רענון",
    "Test": "בדיקה",
    "TRACKER LINK": "קישור עוקב",
    "Choose the USB device and test the connection before continuing.": (
        "בחרו התקן USB ובדקו את החיבור לפני ההמשך."
    ),
    "DRONE RECEIVER VIDEO": "וידאו מקלט רחפן",
    "Choose the feed containing the drone telemetry QR code.": "בחרו את הערוץ עם קוד ה-QR של הרחפן.",
    "No tracker found - check the USB cable": "לא נמצא עוקב - בדקו כבל USB",
    "No video": "אין וידאו",
    "Press Test to check the tracker.": "לחצו בדיקה כדי לבדוק את העוקב.",
    "Testing... please wait": "בודק... המתינו",
    "Set the tracker location": "מיקום העוקב",
    "Enter the 12-digit UTM grid reference and verify the position on the map.": (
        "הזינו רשת UTM בת \u206612\u2069 ספרות ואמתו את המיקום במפה."
    ),
    "e.g. 667000": "למשל \u2066667000\u2069",
    "e.g. 550500": "למשל \u2066550500\u2069",
    "Drone takes off next to the antenna": "הרחפן ממריא ליד האנטנה",
    "Easting \u00b7 first 6 digits": "מזרח \u00b7 \u20666\u2069 ספרות ראשונות",
    "Northing \u00b7 last 6 digits": "צפון \u00b7 \u20666\u2069 ספרות אחרונות",
    "Site altitude \u00b7 above sea level": "גובה האתר \u00b7 מעל פני הים",
    "Takeoff altitude \u00b7 above sea level": "גובה המראה \u00b7 מעל פני הים",
    "SITE COORDINATES": "קואורדינטות אתר",
    "Use the local six-digit easting and northing values.": "השתמשו בערכי מזרח וצפון בני שש ספרות.",
    "\u2714 Found it: {lat}, {lon}  (check the map)": "\u2714 נמצא: {lat}, {lon}  (בדקו במפה)",
    "Please enter the {name} (6 digits).": "נא להזין {name} (\u20666\u2069 ספרות).",
    "easting": "מזרח",
    "northing": "צפון",
    "The {name} must contain digits only.": "{name} חייב להכיל ספרות בלבד.",
    "The {name} must be exactly 6 digits (you entered {count}).": (
        "{name} חייב להכיל בדיוק \u20666\u2069 ספרות (הוזנו {count})."
    ),
    "Enter 12 digits: 6 for easting, then 6 for northing.": (
        "הזינו \u206612\u2069 ספרות: \u20666\u2069 למזרח ואז \u20666\u2069 לצפון."
    ),
    (
        "That position ({lat}, {lon}) is outside Israel. "
        "Check that the easting and northing are not swapped or mistyped."
    ): "המיקום ({lat}, {lon}) מחוץ לישראל. בדקו שהמזרח והצפון לא הוחלפו או הוקלדו שגוי.",
    "  (Recommended)": "  (מומלץ)",
    "Simulated tracker": "עוקב מדומה",
    "Could not open {device}: {err}": "לא ניתן לפתוח את {device}: {err}",
    "Tracker found (pan {pan}, tilt {tilt})": "העוקב נמצא (פאן {pan}, טילט {tilt})",
    "No tracker answered on {device}: {err}": "אין מענה מהעוקב ב-{device}: {err}",
    "No reply to GET": "אין מענה ל-GET",
    "Port {device} not found": "היציאה {device} לא נמצאה",
    "No tracker answered: {err}": "אין מענה מהעוקב: {err}",
    "Simulated power off": "מתח הסימולציה כבוי",
    "Tracker port disappeared": "יציאת העוקב נעלמה",
    "Tracker stopped answering": "העוקב הפסיק לענות",
    "Tracker rebooted": "העוקב אותחל",
    "Serial error: {err}": "שגיאת תקשורת: {err}",
    "Video device not found": "התקן הווידאו לא נמצא",
}


def normalized_language(code: str | None) -> str:
    """English only for the exact code ``en``. Everything else is Hebrew."""
    return "en" if code == "en" else "he"


def set_language(code: str | None) -> None:
    global _LANGUAGE
    _LANGUAGE = normalized_language(code)


def is_rtl() -> bool:
    return _LANGUAGE != "en"


def t(source: str) -> str:
    if _LANGUAGE == "en":
        return source
    return _HE.get(source, source)


def ltr(value: object) -> str:
    """Keep a number or Latin fragment in order inside a Hebrew line."""
    text = str(value)
    if not text or not is_rtl():
        return text
    if text.startswith("\u2066") and text.endswith("\u2069"):
        return text
    return f"\u2066{text}\u2069"


def hebrew_translations() -> dict[str, str]:
    return dict(_HE)
