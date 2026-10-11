import json
import re

from google.genai import errors

MODEL = "gemma-4-26b-a4b-it"


def ask(client, prompt):
    try:
        result = client.models.generate_content(
            model=MODEL,
            contents=prompt,
        )
    except errors.APIError as error:
        raise RuntimeError(f"Gemma unavailable ({error.code}).") from error
    if not result.text:
        raise RuntimeError("Gemma returned no response.")
    return result.text.strip()


def get_action(client, question):
    prompt = f"""
Return only JSON for this medical-centre request.
Actions: list_doctors, list_events, centre_information, book_appointment,
cancel_appointment, edit_doctor, answer.
Use YYYY-MM-DD dates. For answer use a reply field. For schedule edits use
doctor_name and any working_days, working_hours, daily_capacity, admin_pin.
Question: {question}
"""
    text = ask(client, prompt)
    text = re.sub(r"```(?:json)?", "", text, flags=re.IGNORECASE).replace("```", "").strip()
    try:
        result = json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start < 0 or end <= start:
            return {"action": "answer", "reply": "I could not understand that request. Please try again."}
        try:
            result = json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            return {"action": "answer", "reply": "I could not understand that request. Please try again."}
    if not isinstance(result, dict) or "action" not in result:
        return {"action": "answer", "reply": "I could not understand that request. Please try again."}
    return result


def local_reply(result):
    if result.get("error") or result.get("message"):
        return result.get("error") or result["message"]
    if "doctors" in result:
        return "\n".join(
            f"{d['name']} ({d['specialization']}): {d['working_days']}, "
            f"{d['working_hours']}; {d['remaining_slots']} slots"
            for d in result["doctors"]
        ) or "No doctors found."
    if "hours" in result:
        hours = "; ".join(f"{x['day_group']}: {x['timings']}" for x in result["hours"])
        phones = "; ".join(f"{x['contact_person']}: {x['phone']}" for x in result["contacts"])
        return f"Hours: {hours}\nContacts: {phones}"
    if "events" in result:
        return "\n".join(f"{x['title']} on {x['event_date']} at {x['location']}"
                         for x in result["events"]) or "No events."
    return "Done."


def reply(client, question, result):
    if result.get("action") == "answer":
        return result.get("reply", "Please provide more details.")
    try:
        return ask(client, f"Answer briefly using only this data: {result}\nQuestion: {question}")
    except RuntimeError:
        return local_reply(result)
