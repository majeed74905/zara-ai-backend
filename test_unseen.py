import sys
from app.services.language_detector import detect_language
from app.services.zara_identity import detect_communication_profile

unseen_tests = [
    ("Bro nodejs event loop block aaguthu, profiling eppadi start panradhu?", "Tanglish", "casual"),
    ("Respected team, could you elucidate the caching invalidation strategy for multi-region Redis clusters?", "English", "formal"),
    ("I am a school student, what is Docker container in simple words?", "English", "beginner"),
    ("Kafka consumer lag keeps spiking every morning at 9am, cpu is idle though", "English", "technical"),
    ("இந்த python script ஏன் memory leak ஆகுது?", "Tamil", "technical"),
    ("arre yaar ye flutter app build hi nahi ho raha gradle sync fail", "Hinglish", "casual"),
    ("Bro I am fed up with this CSS flexbox centering issue waste of time", "English", "casual"),
    ("give 3 bullet points only", "English", "short_direct"),
    ("PostgreSQL foreign keys create panrappo indexing automatic ah create aaguma?", "Tanglish", "technical"),
    ("machi semma speed ah irukku Zara, thanks da!", "Tanglish", "casual"),
]

all_ok = True
for idx, (text, exp_lang, exp_style) in enumerate(unseen_tests, 1):
    l = detect_language(text)
    p = detect_communication_profile(text)
    lang_ok = (l == exp_lang)
    style_ok = (p["formality"] == exp_style or p["technicality"] == exp_style or p["primary_style"] == exp_style or p["length_pref"] == exp_style)
    print(f"Test {idx}: lang_ok={lang_ok}, style_ok={style_ok} -> Detected Lang={l}, Formality={p['formality']}, Tech={p['technicality']}, Style={p['primary_style']}, Emotion={p['emotion']}")
    if not (lang_ok and style_ok):
        all_ok = False

print("Overall:", "ALL PASSED" if all_ok else "SOME FAILED")
if not all_ok:
    sys.exit(1)
