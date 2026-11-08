"""Records every line in tools/jobs.json with OpenAI's gpt-4o-mini-tts (the ChatGPT-style voices).

Key: OPENAI_API_KEY env var, or a file at tools/.openai_key (gitignored).
Reruns only record lines that changed or were never recorded with OpenAI.
Usage: node tools/make-voice.mjs && python3 tools/make_voice_openai.py
"""
import json, os, sys, time, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'audio')
STATE = os.path.join(OUT, 'engine.json')
MODEL = 'gpt-4o-mini-tts'

HEBREW = ("The listener is Meir, a 5-year-old American boy who just moved to Israel. "
          "Say Hebrew words (Meir, gan, tapuach, kelev, shemesh, kol hakavod, sababa, Ima, Abba, shuk, Shabbat shalom, boker tov) "
          "with natural Israeli Hebrew pronunciation; Meir is pronounced meh-EER.")
VOICES = {
    'rex': dict(voice='coral', instructions=
        "You are Rex, a friendly little dinosaur co-pilot in a space adventure game. Speak warmly and naturally, "
        "with real excitement and a smile, like a fun older sibling talking to a 5-year-old. Clear, not too fast, never sing-song. " + HEBREW),
    'glitch': dict(voice='ash', instructions=
        "You are Glitch, a goofy cartoon space-slime villain. Silly, mischievous, slightly gravelly and teasing, "
        "funny rather than scary, for a 5-year-old audience."),
}
# Phonics sounds: the text is a spelled-out sound (sss, tuh); tell the model which letter it is.
PH_LETTER = {'ah':'a (short a, as in apple)','buh':'b','kuh':'c / k','duh':'d','eh':'e (short e, as in egg)','fff':'f','guh':'g (hard g, as in goat)',
  'huh':'h','ih':'i (short i, as in insect)','juh':'j','lll':'l','mmm':'m','nnn':'n','aw':'o (short o, as in octopus)','puh':'p','rrr':'r',
  'sss':'s','tuh':'t','uh':'u (short u, as in umbrella)','vvv':'v','wuh':'w','ks':'x','yuh':'y','zzz':'z','shhh':'sh','chuh':'ch','thhh':'th (as in thumb)'}

def key():
    k = os.environ.get('OPENAI_API_KEY')
    p = os.path.join(ROOT, 'tools', '.openai_key')
    if not k and os.path.exists(p):
        k = open(p).read().strip()
    if not k:
        sys.exit('No OpenAI key. Set OPENAI_API_KEY or put it in tools/.openai_key')
    return k

def request(job, api_key):
    if job['v'] == 'ph':
        letter = PH_LETTER.get(job['text'], job['text'])
        body = dict(model=MODEL, voice='coral', input=job['text'], instructions=
            f"You are a kind kindergarten phonics teacher. Say ONLY the isolated phonics sound of the letter {letter}, "
            "once, short and clean, the way teachers model letter sounds. Do not say the letter's name and add no other words.")
    else:
        body = dict(model=MODEL, input=job['raw'], **VOICES[job['v']])
    body['response_format'] = 'mp3'
    req = urllib.request.Request('https://api.openai.com/v1/audio/speech', data=json.dumps(body).encode(),
        headers={'Authorization': 'Bearer ' + api_key, 'Content-Type': 'application/json'})
    return urllib.request.urlopen(req, timeout=60).read()

def main():
    api_key = key()
    jobs = json.load(open(os.environ.get('JOBS') or os.path.join(ROOT, 'tools', 'jobs.json')))
    state = json.load(open(STATE)) if os.path.exists(STATE) else {}
    todo = [j for j in jobs if state.get(j['key']) != MODEL or not os.path.exists(os.path.join(OUT, j['key'] + '.mp3'))]
    print(f'{len(todo)} of {len(jobs)} lines to record')
    failures = []
    def run(j):
        for attempt in range(4):
            try:
                data = request(j, api_key)
                path = os.path.join(OUT, j['key'] + '.mp3')
                open(path + '.tmp', 'wb').write(data); os.replace(path + '.tmp', path)
                state[j['key']] = MODEL
                return
            except urllib.error.HTTPError as e:
                err = f'{e.code} {e.read()[:200]!r}'
                if e.code in (400, 401, 403): break
            except Exception as e:
                err = repr(e)
            time.sleep(2 + attempt * 3)
        failures.append((j['key'], j.get('raw', j['text']), err))
    with ThreadPoolExecutor(6) as ex:
        list(ex.map(run, todo))
    json.dump(state, open(STATE, 'w'), indent=0)
    have = sorted(f[:-4] for f in os.listdir(OUT) if f.endswith('.mp3'))
    json.dump(have, open(os.path.join(OUT, 'manifest.json'), 'w'))
    print(f'{len(todo) - len(failures)} recorded, {len(failures)} failed')
    for f in failures[:10]:
        print('FAILED', *f)
    sys.exit(1 if failures else 0)

main()
