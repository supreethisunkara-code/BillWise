"""
Same conversation logic as the prototype, with two changes:
  1. Synchronous (no async/await -- not needed in a single-shot Lambda).
  2. Session state read/written through src/session_store.py (DynamoDB)
     instead of an in-memory dict, so it survives across Lambda invocations
     that may land on different containers.
"""
from src import overcharge_checker, insurance, schemes, session_store
from src.session_store import Session


def format_bill_summary(bill_data: dict) -> str:
    lines = ["*Here's your bill breakdown:*\n"]
    totals_by_category: dict[str, float] = {}
    for item in bill_data.get("line_items", []):
        cat = item.get("category", "other")
        totals_by_category[cat] = totals_by_category.get(cat, 0) + (item.get("amount") or 0)

    for cat, total in sorted(totals_by_category.items(), key=lambda x: -x[1]):
        lines.append(f"• {cat.replace('_', ' ').title()}: ₹{total:,.0f}")

    if bill_data.get("total_amount"):
        lines.append(f"\n*Total: ₹{bill_data['total_amount']:,.0f}*")

    if bill_data.get("extraction_confidence") == "low":
        lines.append("\n⚠️ Some parts of the bill were hard to read clearly -- double check the numbers above.")

    return "\n".join(lines)


def format_overcharge_flags(flags: list[dict]) -> str:
    if not flags:
        return "✅ Nothing obviously out of line compared to typical reference rates."
    lines = ["*A few things worth asking the billing desk about:*\n"]
    for f in flags:
        amt_str = f" (₹{f['amount']:,.0f})" if f.get("amount") else ""
        lines.append(f"• {f['description']}{amt_str}\n  → {f['reason']}")
    return "\n\n".join(lines)


def format_scheme_results(results: list[dict]) -> str:
    lines = ["*Government scheme check:*\n"]
    for r in results:
        if r["likely_eligible"] is True:
            marker = "✅ Possibly eligible"
        elif r["likely_eligible"] is False:
            marker = "❌ Probably not eligible"
        else:
            marker = "❓ Worth checking"
        lines.append(f"{marker} -- *{r['scheme_name']}*\n{r['note']}\nCheck: {r['check_url']}")
        if r.get("helpline"):
            lines[-1] += f" | Helpline: {r['helpline']}"
    return "\n\n".join(lines)


def format_insurance_estimate(est: dict) -> str:
    lines = [
        "*Rough insurance coverage estimate:*\n",
        f"Likely covered: ₹{est['likely_covered_estimate']:,.0f}",
        f"Likely excluded/capped: ₹{est['likely_excluded_estimate']:,.0f}",
    ]
    if est["needs_manual_review"]:
        lines.append(f"\n{len(est['needs_manual_review'])} item(s) (e.g. room rent) depend on your "
                      f"policy's specific capping -- check your policy document for these.")
    lines.append(f"\n_{est['disclaimer']}_")
    return "\n".join(lines)


def handle_bill_upload(user_id: str, bill_data: dict) -> str:
    session = Session(stage="ASK_INSURANCE", bill_data=bill_data)
    session_store.save_session(user_id, session)

    summary = format_bill_summary(bill_data)
    flags = overcharge_checker.check_overcharges(bill_data.get("line_items", []))
    flag_text = format_overcharge_flags(flags)

    prompt = (
        "\n\nDo you have health insurance for this admission? Reply *yes* or *no*.\n"
        "(Or reply *skip* to jump straight to the government scheme check.)"
    )
    return f"{summary}\n\n{flag_text}{prompt}"


def handle_insurance_response(user_id: str, session: Session, text: str) -> str:
    text_lower = text.strip().lower()

    if text_lower in ("yes", "y"):
        session.has_insurance = True
        est = insurance.estimate_coverage(session.bill_data.get("line_items", []))
        session.stage = "ASK_SCHEME_INFO"
        session_store.save_session(user_id, session)
        return (
            format_insurance_estimate(est)
            + "\n\nNow let's check government scheme eligibility too. "
              "What's your approximate *annual family income* in ₹?"
        )
    elif text_lower in ("no", "n", "skip"):
        session.has_insurance = False
        session.stage = "ASK_SCHEME_INFO"
        session_store.save_session(user_id, session)
        return "No problem. What's your approximate *annual family income* in ₹?"
    else:
        return "Please reply *yes*, *no*, or *skip*."


def handle_scheme_info(user_id: str, session: Session, text: str) -> str:
    if session.annual_income is None:
        try:
            session.annual_income = float(text.replace(",", "").strip())
        except ValueError:
            return "Please send just the number, e.g. 180000"
        session_store.save_session(user_id, session)
        return "Which *state* are you in?"

    if session.state_name is None:
        session.state_name = text.strip()
        session_store.save_session(user_id, session)
        return (
            "What's your employment situation? Reply one of:\n"
            "*central_govt* / *state_govt* / *private* / *self_employed* / *unemployed*"
        )

    if session.employment_type is None:
        session.employment_type = text.strip().lower()
        results = schemes.check_eligibility(
            annual_income=session.annual_income,
            state=session.state_name,
            employment_type="central_govt_employee" if session.employment_type == "central_govt" else session.employment_type,
        )
        session.stage = "DONE"
        session_store.save_session(user_id, session)
        return (
            format_scheme_results(results)
            + "\n\nThat's the full picture for this bill. Send another bill photo anytime to start over."
        )

    session_store.reset_session(user_id)
    return "Let's start fresh -- send a photo of your hospital bill."


def route_message(user_id: str, message_type: str, text: str | None, bill_bytes: bytes | None,
                    content_type: str, extract_bill_fn) -> str:
    """
    Main entry point. `extract_bill_fn` is injected (bill_parser.extract_bill)
    so this stays testable without hitting the real Anthropic API.
    """
    session = session_store.get_session(user_id)

    if message_type in ("image", "document") and bill_bytes:
        try:
            bill_data = extract_bill_fn(bill_bytes, content_type)
        except ValueError:
            return ("Sorry, I couldn't read that bill clearly. Could you resend a clearer photo "
                    "(good lighting, flat page, all corners visible)?")
        return handle_bill_upload(user_id, bill_data)

    if session.stage == "ASK_INSURANCE" and text:
        return handle_insurance_response(user_id, session, text)

    if session.stage == "ASK_SCHEME_INFO" and text:
        return handle_scheme_info(user_id, session, text)

    if session.stage == "DONE" and text:
        session_store.reset_session(user_id)
        return "Send a photo of your next hospital bill to get started."

    return ("Hi! Send me a clear photo or PDF of your hospital bill and I'll break it down for you, "
            "flag anything that looks overcharged, and check government scheme + insurance coverage.")