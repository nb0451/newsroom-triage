# Newsroom Triage

Paste a news headline, get a category, see exactly how it decided.

Built for Week 2 of the AI and Machine Learning mentorship programme.

## Run it

    pip install -r requirements.txt
    python run.py

Open http://127.0.0.1:7860

With no `GROQ_API_KEY` set it runs on a built-in stand-in classifier, so it
works before you have signed up for anything. The Health tab tells you which
mode you are in.

## The only file you need to change

`app/config.py`. It is almost entirely plain English: the prompt, the routing
rules, the guardrails, and which notes the app may read from.

## Tests

    pytest -q

Seventeen tests. Three fail on purpose and describe the three things the
assistant is missing. They turn green when you fix `app/config.py`.
