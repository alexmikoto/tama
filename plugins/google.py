"""
google.py

Originally for RoboCop 2, a replacement after Google's deprecation of Google Web Search API
Module requires a Google Custom Search API key and a Custom Search Engine ID in order to function.
Ported from CloudBot.

Created By:
    - Foxlet <http://furcode.tk/>

License:
    GNU General Public License (Version 3)
"""
import random

from tama import api
from tama.util import http
from tama.util.legacy import formatting, filesize

API_CS = 'https://www.googleapis.com/customsearch/v1'
DEPRECATED_API = 'http://ajax.googleapis.com/ajax/services/search/web'

dev_key: str = None  # noqa
cx: str = None  # noqa


@api.on_load()
def load_api(config: dict = None):
    global dev_key
    global cx

    dev_key = config.get("google_dev_key", None)
    cx = config.get("google_cse_id", None)


# This command will be disabled until the deprecated Google Search API is dropped.
@api.command('g', 'google', 'gse')
async def gse(text):
    """<query> -- Returns first Google search result for <query>."""
    if not dev_key:
        return "This command requires a Google Developers Console API key."
    if not cx:
        return "This command requires a custom Google Search Engine ID."

    parsed = await http.get_json(
        API_CS, params={"cx": cx, "q": text, "key": dev_key}
    )

    try:
        result = parsed['items'][0]
    except KeyError:
        return "No results found."

    title = formatting.truncate(result['title'], 60)
    content = result['snippet']

    if not content:
        content = "No description available."
    else:
        content = formatting.truncate(content.replace('\n', ''), 150)

    return u'{} -- \x02{}\x02: "{}"'.format(result['link'], title, content)


@api.command('gis','image', 'googleimage')
async def gse_gis(text):
    """<query> -- Returns first Google Images result for <query>."""
    if not dev_key:
        return "This command requires a Google Developers Console API key."
    if not cx:
        return "This command requires a custom Google Search Engine ID."

    parsed = await http.get_json(
        API_CS,
        params={"cx": cx, "q": text, "searchType": "image", "key": dev_key}
    )

    try:
        r = random.randrange(len(parsed['items']))
        result = parsed['items'][r]
        metadata = parsed['items'][r]['image']
    except (KeyError, ValueError):
        return "No results found."

    dimens = '{}x{}px'.format(metadata['width'], metadata['height'])
    size = filesize.size(int(metadata['byteSize']))

    return u'{} [{}, {}, {}]'.format(result['link'], dimens, result['mime'], size)
