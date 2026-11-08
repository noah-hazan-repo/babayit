"""Records every line in tools/jobs.json with Microsoft neural voices (edge-tts). Reruns only fill in missing clips."""
import asyncio, json, os, sys
import edge_tts

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'audio')
VOICES = {
    'rex': dict(voice='en-US-AnaNeural', rate='+0%', pitch='+0Hz'),
    'ph': dict(voice='en-US-AnaNeural', rate='-20%', pitch='+0Hz'),
    'glitch': dict(voice='en-US-GuyNeural', rate='-10%', pitch='-25Hz'),
}

async def make(job, sem, failures):
    path = os.path.join(OUT, job['key'] + '.mp3')
    if os.path.exists(path) and os.path.getsize(path) > 0:
        return
    cfg = VOICES[job['v']]
    async with sem:
        for attempt in range(3):
            try:
                await edge_tts.Communicate(job['text'], **cfg).save(path + '.tmp')
                os.replace(path + '.tmp', path)
                return
            except Exception as e:
                err = e
                await asyncio.sleep(1 + attempt * 2)
        failures.append((job['key'], job['text'], repr(err)))

async def main():
    os.makedirs(OUT, exist_ok=True)
    jobs = json.load(open(os.path.join(ROOT, 'tools', 'jobs.json')))
    keep = {j['key'] for j in jobs}
    for f in os.listdir(OUT):
        if f.endswith('.mp3') and f[:-4] not in keep:
            os.remove(os.path.join(OUT, f))
    sem, failures = asyncio.Semaphore(8), []
    await asyncio.gather(*(make(j, sem, failures) for j in jobs))
    have = sorted(j['key'] for j in jobs if os.path.exists(os.path.join(OUT, j['key'] + '.mp3')))
    json.dump(have, open(os.path.join(OUT, 'manifest.json'), 'w'))
    print(f'{len(have)}/{len(jobs)} clips')
    for f in failures:
        print('FAILED', *f)
    sys.exit(1 if failures else 0)

asyncio.run(main())
