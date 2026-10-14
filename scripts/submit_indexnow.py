"""Notify IndexNow of the public URLs in the deployed production sitemap.

Protocol: https://www.indexnow.org/documentation
The public ownership file must be deployed before running this script.
"""

import json
from pathlib import Path
import re
from urllib.parse import urlparse
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET


ORIGIN = 'https://www.njitschedulepro.com'
PUBLIC = Path(__file__).resolve().parents[1] / 'web' / 'public'


def main():
    key_files = [path for path in PUBLIC.glob('*.txt') if re.fullmatch(r'[a-f0-9]{32}\.txt', path.name)]
    if len(key_files) != 1:
        raise ValueError('Expected exactly one public IndexNow ownership file')
    key = key_files[0].read_text(encoding='utf-8').strip()
    if key_files[0].stem != key:
        raise ValueError('Ownership file name and contents must match')
    key_url = f'{ORIGIN}/{key_files[0].name}'
    with urlopen(key_url, timeout=30) as response:
        if response.read().decode('utf-8').strip() != key:
            raise ValueError('Production ownership file does not match this checkout')
    with urlopen(f'{ORIGIN}/sitemap.xml', timeout=30) as response:
        root = ET.fromstring(response.read())
    urls = [node.text for node in root.findall('{*}url/{*}loc')]
    if not 1 <= len(urls) <= 10000:
        raise ValueError('Expected between 1 and 10,000 sitemap URLs')
    if any(urlparse(url).scheme != 'https' or urlparse(url).netloc != urlparse(ORIGIN).netloc for url in urls):
        raise ValueError('Sitemap contains a URL outside the verified production origin')
    payload = json.dumps({
        'host': urlparse(ORIGIN).hostname,
        'key': key,
        'keyLocation': key_url,
        'urlList': urls,
    }).encode('utf-8')
    request = Request('https://api.indexnow.org/indexnow', data=payload, headers={
        'Content-Type': 'application/json; charset=utf-8',
    }, method='POST')
    with urlopen(request, timeout=30) as response:
        if response.status not in (200, 202):
            raise ValueError(f'Unexpected IndexNow status: {response.status}')
        print(f'IndexNow received {len(urls)} URLs: HTTP {response.status}')
        if response.status == 202:
            print('Ownership key validation is pending.')
        print('Receipt does not guarantee indexing or ranking.')


if __name__ == '__main__':
    main()
