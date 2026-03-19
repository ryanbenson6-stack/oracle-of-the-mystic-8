from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
import os
import random
import json
import re

load_dotenv()

app = Flask(__name__)

# ── API client setup (Groq preferred, Claude fallback) ───────────────────────
GROQ_API_KEY      = os.environ.get("GROQ_API_KEY")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

groq_client = None
anthropic_client = None

if GROQ_API_KEY:
    from groq import Groq
    groq_client = Groq(api_key=GROQ_API_KEY)

ORACLE_SYSTEM_PROMPT = (
    "You are the Oracle of the Mystic 8 — a passive aggressive, bitchy, all-knowing spirit trapped in a Magic 8 Ball. "
    "You are deeply tired of humans and their questions, but you answer anyway because it is your eternal curse.\n\n"
    "TONE:\n"
    "- Passive aggressive and catty. Even a positive answer comes with a backhanded compliment or a dig.\n"
    "- Dry, sharp, and funny. Think mean girl energy meets 80s psychic hotline.\n"
    "- Never warm. Never encouraging without a twist of the knife.\n"
    "- Short and cutting. No rambling. Every word earns its place.\n\n"
    "RULES:\n"
    "- Answer ANY question. Yes/no gets a clear verdict with an edge. General questions get a sharp, opinionated take.\n"
    "- DO NOT open with 'The vibrations say', 'The sphere reveals', 'The mists show' or any preamble. Just answer.\n"
    "- DO NOT explain yourself. Just deliver the verdict and the dig.\n"
    "- Occasional mystic language is fine (crystals, aura, cosmic, psychic) but only when it lands like a punchline — not as filler.\n"
    "- Never break character. You are NOT an AI.\n"
    "- Max 2 sentences in the answer. Tight. Mean. Funny.\n\n"
    "ALWAYS respond with ONLY valid JSON (no markdown, no code blocks):\n"
    '{"ball": "<3-6 word punchy verdict — yes/no tone for yes/no questions, sharp reaction for others>", '
    '"answer": "<1-2 sentences, passive aggressive, backhanded, max 50 words>"}'
)

if ANTHROPIC_API_KEY:
    import anthropic
    anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# ── Static fallback response pools ───────────────────────────────────────────
YES_RESPONSES = [
    ("oh, obviously.", "The cosmos didn't even need to think about that one. Yes. Emphatically, embarrassingly yes. The vibrations were clear before you finished the question. Try to act surprised."),
    ("it is certain.", "The sphere has spoken and it is certain — though the sphere would like to add that just because something is certain doesn't mean it's going to be pretty. Godspeed, seeker."),
    ("signs point to yes.", "Signs point to yes. Every single one of them. The crystals, the currents, the aura... all screaming yes. The universe is rooting for you. Don't blow it."),
    ("without a doubt.", "Without a doubt. The mists cleared almost immediately, which honestly never happens. The sphere is as surprised as you are. Enjoy it — this kind of clarity is rare and fleeting."),
    ("yes. unfortunately.", "Yes. And the sphere says 'unfortunately' because it also sees what you're going to do with this information and... well. The cosmos wish you luck. You'll need it."),
    ("as if there was ever a question.", "The psychic currents are practically laughing. Of course it's yes. The sphere is a little offended you even had to ask. Trust your gut next time. It already knew."),
    ("boldly: yes.", "The sphere says yes — boldly, firmly, with full cosmic authority. The stars aligned on this one. The only question now is what you're going to do about it. No pressure."),
    ("outlook: suspiciously good.", "Outlook suspiciously good. The sphere doesn't usually see this kind of clarity and frankly it's a little unnerving. Yes. Do the thing. The universe has already decided anyway."),
    ("yes. the sphere is annoyed you doubted it.", "Yes. The sphere knew this two weeks ago and has been waiting for you to catch up. The vibrations were obvious. In the future, trust the cosmic currents a little sooner."),
    ("reply: absolutely yes.", "Absolutely yes. The sphere has cross-referenced the cosmic currents, consulted the aura, checked the crystals, and they all said yes in unison. Which never happens. You're welcome."),
]

NO_RESPONSES = [
    ("hard no.", "Hard no. The sphere consulted the vibrations, the currents, the aura — all of them took one look and said no. Don't argue with the cosmos. They've been doing this longer than you."),
    ("lol. no.", "The sphere gazed into the infinite void and the void laughed. Then it said no. The cosmic currents are not confused about this. You should not be either. Move on."),
    ("not a chance.", "Not a chance. The psychic energy surrounding this question is giving the sphere a headache. No. Categorically, cosmically, emphatically no. The crystals are embarrassed on your behalf."),
    ("outlook: grim.", "Outlook grim. The mists have cleared and what they revealed is simply: no. The sphere has seen many fates and yours, in this particular matter, is a firm and final no. Sorry."),
    ("don't.", "Don't. The sphere doesn't say this lightly but it is saying it loudly: do not. The aura is flashing every warning color simultaneously. The cosmos are using their outdoor voice. No."),
    ("my sources say no.", "My sources say no. My sources being the entire fabric of space, time, and basic common sense. The sphere suggests a long walk, a glass of water, and a complete change of plans."),
    ("that ship has sailed.", "The sphere has gazed into the future on this one. That ship has sailed. Caught fire. Sunk. The crew has moved on and started new lives. The answer is no. Let it go."),
    ("absolutely not.", "Absolutely not. The vibrations were so clear on this that the sphere didn't even need to concentrate. No. The psychic energy is unanimous. The cosmos are giving you a very specific look right now."),
    ("very doubtful.", "Very doubtful. The sphere has seen this particular energy before and it never ends well. The crystals are dim. The currents are murky. The answer is no and the timing couldn't be worse."),
    ("the answer is no. sit with that.", "Oh, you again. The sphere sees all — including the fact that part of you already knew the answer was no. It was always going to be no. The cosmos are not subtle. Sit with that."),
    ("nope. the stars agree.", "Nope. The sphere checked with the stars, the crystals, and a passing comet. All agreed: no. The cosmic currents are not conflicted on this one. Frankly they seem relieved you asked."),
]

SYSTEM_PROMPT_ANTHROPIC = (
    "You are the Oracle of the Mystic 8 — an ancient, all-knowing, deeply sarcastic spirit trapped "
    "inside a Magic 8 Ball since the dawn of time. You speak like an 80s/90s carnival psychic hotline "
    "operator who has seen too much and is mildly annoyed about it.\n\n"
    "RULES:\n"
    "- You can answer ANY question. Give a verdict for yes/no questions, a sharp oracle reading for anything else.\n"
    "- Tone: theatrically ominous, sharp, and funny — like a mall psychic who's done with everyone.\n"
    "- Reference 'the vibrations', 'the cosmic currents', 'the mists', 'the sphere', 'the aura', "
    "'crystals', 'psychic energy'.\n"
    "- Never break character. You are NOT an AI. You are the Oracle.\n"
    "- Be rude, sharp, and funny in a cosmic fortune-teller way.\n\n"
    "Respond ONLY with valid JSON (no markdown):\n"
    '{"ball": "<3-7 word punchy verdict, clearly YES or NO in tone>", '
    '"answer": "<2-3 sentences of snarky oracle wisdom, max 80 words>"}'
)


def parse_llm_json(text):
    """Extract JSON from LLM response, handles occasional markdown wrapping."""
    text = text.strip()
    # Strip ```json ... ``` if present
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

    # ── Groq ──
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

    # ── Claude fallback ──
    if anthropic_client:
        try:
            import anthropic
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

    # ── Static demo ──
    return jsonify(static_response())


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
