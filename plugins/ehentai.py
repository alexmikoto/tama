import re
import requests

from tama import api

eh_re = re.compile(r'hentai.org/g/(\d+)/(\w+)', re.I)


def get_eh(gid: str, gtoken: str):
    r = requests.post("https://api.e-hentai.org/api.php", json={
        "method": "gdata",
        "gidlist": [
            [gid, gtoken]
        ],
        "namespace": 1
    })
    result = r.json()
    metadata = result['gmetadata']
    title = metadata[0]["title"]
    return f"\x02{title}\x02"


@api.regex(eh_re)
def eh_url(match: re.Match):
    return get_eh(match.group(1), match.group(2))
