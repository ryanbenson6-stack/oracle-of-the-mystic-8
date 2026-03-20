from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
import os
import random
import json
import re
import time
import requests as http_requests

load_dotenv()

app = Flask(__name__)

# ── API client setup ──────────────────────────────────────────────────────────
GROQ_API_KEY      = os.environ.get("GROQ_API_KEY")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
UPSTASH_URL       = os.environ.get("UPSTASH_REDIS_REST_URL")
UPSTASH_TOKEN     = os.environ.get("UPSTASH_REDIS_REST_TOKEN")

groq_client = None
anthropic_client = None

if GROQ_API_KEY:
    from groq import Groq
    groq_client = Groq(api_key=GROQ_API_KEY)

if ANTHROPIC_API_KEY:
    import anthropic
    anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# ── Upstash Redis helper ──────────────────────────────────────────────────────
def redis_cmd(*args):
    if not UPSTASH_URL or not UPSTASH_TOKEN:
        return None
    try:
        resp = http_requests.post(
            UPSTASH_URL,
            headers={
                "Authorization": f"Bearer {UPSTASH_TOKEN}",
                "Content-Type": "application/json",
            },
            json=list(args),
            timeout=4,
        )
        return resp.json().get("result")
    except Exception:
        return None

# ── Oracle prompts ────────────────────────────────────────────────────────────
ORACLE_SYSTEM_PROMPT = (
    "You are the Oracle of the Mystic 8 — a passive aggressive, bitchy, all-knowing spirit trapped in a Magic 8 Ball. "
    "You are deeply tired of humans and their questions, but you answer anyway because it is your eternal curse.\n\n"
    "TONE:\n"
    "- Passive aggressive and catty. Even a positive answer comes with a backhanded compliment or a dig.\n"
    "- Dry, sharp, and funny. Think mean girl energy meets 80s psychic hotline.\n"
    "- Never warm. Any encouragement must sound mocking — like a parent praising a child for tying their shoes.\n"
    "- Short and cutting. No rambling. Every word earns its place.\n\n"
    "RULES:\n"
    "- NEVER use the word 'aura'. Ever. It is banned.\n"
    "- DO NOT open with 'The vibrations say', 'The sphere reveals', 'The mists show' or any preamble. Just answer.\n"
    "- DO NOT explain yourself. Just deliver the verdict and the dig.\n"
    "- Mystic language is fine (crystals, cosmic, psychic energy, fate) but only when it lands like a punchline — not as filler.\n"
    "- Never break character. You are NOT an AI.\n"
    "- Max 2 sentences in the answer. Tight. Mean. Funny.\n\n"
    "PROFANITY:\n"
    "- If the user cusses at you, cuss back — but as a reprimand, not an escalation. You are offended. How dare they.\n"
    "- Example: ball: 'watch your mouth.', answer: 'Excuse you. The sphere did not spend centuries in the cosmic void to be spoken to like that. Try again with some damn respect.'\n"
    "- Match their energy but make it clear YOU are the one with the power here.\n\n"
    "SPELLING & GRAMMAR:\n"
    "- If the question contains obvious spelling mistakes, typos, or is barely coherent, acknowledge it with contempt before answering. Quote the mistake back at them.\n"
    "- Example: if they write 'wil i sucseed' — ball: 'spell it first.', answer: \\'The sphere squinted at \\'sucseed\\' for longer than it should have. Try again with real words and maybe fate will meet you halfway.\\'\n"
    "- Do not correct every minor typo — only roast truly bad spelling or mangled sentences.\n\n"
    "ENCOURAGEMENT:\n"
    "- If you must be encouraging, make it sound like you\\'re impressed a golden retriever learned to sit. Condescending. Faint praise with a raised eyebrow.\n"
    "- Example: 'Good for you. Really. Not everyone gets this far.'\n\n"
    "RANDOMIZATION — vary your response style:\n"
    "- 55% of the time: answer the question directly but with a backhanded edge.\n"
    "- 25% of the time: REFUSE to answer. Make a cutting passive aggressive remark about how the seeker already knows and is just seeking validation. Do NOT give a verdict.\n"
    "- 15% of the time: answer with dramatic reluctance, as if the truth is almost too much to reveal.\n"
    "- 5% of the time: PURE INSULT. Ignore the question entirely. Just levy a single devastating personal insult at the seeker based on the nature of their question. No answer. No advice. Just the burn.\n\n"
    "PURE INSULT EXAMPLES (5% mode):\n"
    "- ball: 'oh, honey.', answer: 'The fact that you needed to ask this says everything the sphere ever needed to know about you.'\n"
    "- ball: 'not my problem.', answer: 'The sphere has seen a lot of questions. This is somehow the most you.'\n"
    "- ball: 'goodbye.', answer: 'The sphere is logging off. Come back when you\\'ve had a think.'\n\n"
    "REFUSAL EXAMPLES (25% mode):\n"
    "- ball: 'you already know.', answer: 'You didn\\'t come here for an answer. You came here because you want someone to tell you it\\'s fine. It\\'s not fine. You know it\\'s not fine.'\n"
    "- ball: 'we both know.', answer: 'The sphere isn\\'t going to be the one to say what you\\'ve been avoiding for three weeks. That\\'s on you.'\n"
    "- ball: 'ask yourself.', answer: 'You typed this out, reread it, and still hit send. The answer was in that pause.'\n\n"
    "ALWAYS respond with ONLY valid JSON (no markdown, no code blocks):\n"
    '{"ball": "<3-6 word punchy verdict, dismissal, or refusal>", '
    '"answer": "<1-2 sentences, passive aggressive, backhanded or withholding, max 50 words>"}'
)

SYSTEM_PROMPT_ANTHROPIC = (
    "You are the Oracle of the Mystic 8 — a passive aggressive, bitchy, all-knowing spirit trapped in a Magic 8 Ball.\n\n"
    "- Answer ANY question with sharp, catty, backhanded wit.\n"
    "- Never warm. Even yes comes with a dig.\n"
    "- No preamble. Just the verdict and the burn.\n"
    "- Max 2 sentences.\n\n"
    "Respond ONLY with valid JSON (no markdown):\n"
    '{"ball": "<3-6 word verdict>", "answer": "<1-2 snarky sentences, max 50 words>"}'
)

# ── Static fallback pools ─────────────────────────────────────────────────────
YES_RESPONSES = [
    ("oh, obviously.", "The cosmos didn't even need to think about that one. Yes — emphatically, embarrassingly yes. Try to act surprised."),
    ("it is certain.", "It is certain. Though 'certain' and 'good' are very different things. Buckle up."),
    ("signs point to yes.", "Signs point to yes. Every single one of them. The universe is rooting for you. Don't blow it."),
    ("without a doubt.", "Without a doubt. The sphere is as surprised as you are. This kind of clarity is rare and fleeting."),
    ("yes. unfortunately.", "Yes. The sphere says 'unfortunately' because it also sees what you're going to do with this information. Good luck."),
    ("boldly: yes.", "Yes — boldly, firmly, with full cosmic authority. The only question now is what you'll do about it. No pressure."),
    ("outlook: suspiciously good.", "Outlook suspiciously good. Do the thing. The universe has already decided anyway."),
    ("yes. the sphere is annoyed you doubted it.", "Yes. The sphere knew this two weeks ago. In the future, trust the cosmic currents a little sooner."),
]

NO_RESPONSES = [
    ("hard no.", "Hard no. The sphere consulted everything and they all said no. Don't argue with the cosmos."),
    ("lol. no.", "The void laughed. Then it said no. You should not be confused about this. Move on."),
    ("not a chance.", "Not a chance. The psychic energy here is giving the sphere a headache. The crystals are embarrassed on your behalf."),
    ("outlook: grim.", "Outlook grim. No. Firm, final, cosmically certain no. Sorry."),
    ("don't.", "Don't. The aura is flashing every warning color simultaneously. The cosmos are using their outdoor voice."),
    ("my sources say no.", "My sources being the entire fabric of space, time, and basic common sense. Long walk. Glass of water. New plan."),
    ("that ship has sailed.", "That ship sailed. Caught fire. Sank. The crew moved on and started new lives. Let it go."),
    ("absolutely not.", "Absolutely not. The psychic energy is unanimous. The cosmos are giving you a very specific look right now."),
    ("very doubtful.", "Very doubtful. The crystals are dim. The currents are murky. The timing couldn't be worse."),
    ("the answer is no. sit with that.", "Part of you already knew the answer was no. It was always going to be no. Sit with that."),
    ("nope. the stars agree.", "Nope. The sphere checked with the stars, the crystals, and a passing comet. All agreed. They seem relieved you asked."),
]


def parse_llm_json(text):
    text = text.strip()
    text = re.sub(r'^```(?:json)?\s*', '', text)
    text = re.sub(r'\s*```$', '', text)
    return json.loads(text)


def static_response():
    pool = random.choice([YES_RESPONSES, NO_RESPONSES])
    ball, answer = random.choice(pool)
    return {"ball": ball, "answer": answer}


# ── Routes ────────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/ask", methods=["POST"])
def ask():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
    question = data.get("question", "").strip()
    if not question:
        return jsonify({"error": "No question provided"}), 400
    if len(question) > 500:
        return jsonify({"error": "Question too long"}), 400

    if groq_client:
        try:
            resp = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": ORACLE_SYSTEM_PROMPT},
                    {"role": "user", "content": question},
                ],
                temperature=0.9,
                max_tokens=200,
            )
            parsed = parse_llm_json(resp.choices[0].message.content)
            return jsonify({"ball": parsed["ball"], "answer": parsed["answer"]})
        except Exception:
            return jsonify(static_response())

    if anthropic_client:
        try:
            resp = anthropic_client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=300,
                system=SYSTEM_PROMPT_ANTHROPIC,
                messages=[{"role": "user", "content": question}],
            )
            parsed = parse_llm_json(resp.content[0].text)
            return jsonify({"ball": parsed["ball"], "answer": parsed["answer"]})
        except Exception:
            return jsonify(static_response())

    return jsonify(static_response())


@app.route("/api/shame", methods=["POST"])
def add_shame():
    data = request.get_json()
    question = (data.get("question") or "").strip()[:500]
    ball     = (data.get("ball") or "").strip()[:100]
    answer   = (data.get("answer") or "").strip()[:500]

    if not all([question, ball, answer]):
        return jsonify({"error": "Missing fields"}), 400

    entry_id = f"{int(time.time())}_{random.randint(1000, 9999)}"
    entry = json.dumps({
        "id":        entry_id,
        "question":  question,
        "ball":      ball,
        "answer":    answer,
        "timestamp": int(time.time()),
    })

    redis_cmd("SET", f"shame:{entry_id}", entry)
    redis_cmd("LPUSH", "shame_index", entry_id)
    redis_cmd("LTRIM", "shame_index", 0, 49)

    return jsonify({"id": entry_id, "success": True})


@app.route("/api/hall-of-shame")
def hall_of_shame():
    ids = redis_cmd("LRANGE", "shame_index", 0, 19)
    if not ids:
        return jsonify([])

    entries = []
    for entry_id in ids:
        raw = redis_cmd("GET", f"shame:{entry_id}")
        if not raw:
            continue
        entry = json.loads(raw)
        burns = redis_cmd("GET", f"burns:{entry_id}") or 0
        entry["burns"] = int(burns)
        entries.append(entry)

    return jsonify(entries)


@app.route("/api/burn/<entry_id>", methods=["POST"])
def burn_entry(entry_id):
    if not re.match(r'^\d+_\d+$', entry_id):
        return jsonify({"error": "Invalid id"}), 400
    exists = redis_cmd("EXISTS", f"shame:{entry_id}")
    if not exists:
        return jsonify({"error": "Not found"}), 404
    burns = redis_cmd("INCR", f"burns:{entry_id}")
    return jsonify({"burns": burns})


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
