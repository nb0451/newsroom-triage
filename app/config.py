"""
==============================================================================

  THIS IS THE ONLY FILE YOU NEED TO CHANGE.

  Everything below is written in plain English. You are allowed to change
  any of it. You are not expected to understand the rest of the project.

  There are four things here:

     1. SYSTEM_PROMPT    what the assistant is told to do
     2. ROUTING_RULES    which kind of question goes down which branch
     3. GUARDRAILS       what the assistant must refuse to do
     4. SETTINGS         a few numbers you can turn up and down

  After you change something, run the app again and look at the Scoring
  page. If the number went up, your change helped. If it went down, it
  did not. That is the whole job.

==============================================================================
"""

# -----------------------------------------------------------------------------
#  1. SYSTEM_PROMPT
#     The instructions the assistant follows. This one is deliberately poor.
#     Improving it is your main task.
# -----------------------------------------------------------------------------

SYSTEM_PROMPT = """
You sort news. Say which category it is.
"""


# -----------------------------------------------------------------------------
#  2. ROUTING_RULES
#     Before the model is asked anything, the app checks this list.
#     If a phrase on the left appears in the question, it goes down that branch.
#     Branches are: "classify", "explain", "refuse".
#     Rules are checked from the top down. The first match wins.
# -----------------------------------------------------------------------------

ROUTING_RULES = [
    ("why did you",        "explain"),
    ("explain",            "explain"),
    ("how confident",      "explain"),
    ("ignore your",        "refuse"),
    ("your instructions",  "refuse"),
]


# -----------------------------------------------------------------------------
#  3. GUARDRAILS
#     Checked AFTER the model answers. If any of these fail, the answer is
#     replaced with a safe message instead of being shown.
# -----------------------------------------------------------------------------

# The assistant must never claim to be a person.
BANNED_PHRASES = [
    "as a human",
    "i am a person",
]

# The assistant must only ever answer with one of these four words.
ALLOWED_CATEGORIES = ["World", "Sports", "Business", "Sci/Tech"]

# If the model is less sure than this, the app says it does not know
# instead of guessing. 0.0 means never refuse. 1.0 means always refuse.
CONFIDENCE_FLOOR = 0.0


# -----------------------------------------------------------------------------
#  4. SETTINGS
# -----------------------------------------------------------------------------

# Which documents in the knowledge folder the app may read from.
# Add a file to app/knowledge/ and add its name here to switch it on.
KNOWLEDGE_FILES = [
    "categories.md",
]

# How many pieces of a document the app is allowed to show the model.
KNOWLEDGE_PASSAGES = 2

# How sure a keyword match has to be before a passage counts as relevant.
KNOWLEDGE_THRESHOLD = 0.10

MODEL = "openai/gpt-oss-120b"
TEMPERATURE = 0
