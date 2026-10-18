# python diag_post.py   (run inside the bot folder, venv active)
import requests
from bs4 import BeautifulSoup
from services.ott_releases import HEADERS, _iter_candidate_post_urls, _extract_release_blocks
urls = _iter_candidate_post_urls()
print("CANDIDATES:", urls)
for u in urls[:3]:
    r = requests.get(u, headers=HEADERS, timeout=15)
    ents = _extract_release_blocks(r.text)
    print("\n", u, r.status_code, "entries:", len(ents))
    for e in ents[:3]: print("  ", e)
    if not ents:
        s = BeautifulSoup(r.text, "html.parser")
        print("  h2/h3/h4/ul:", [len(s.find_all(x)) for x in ("h2","h3","h4","ul")])
        i = r.text.find("Release Date")
        print("  AROUND 'Release Date':", r.text[max(0,i-400):i+500] if i>=0 else "NOT FOUND")
