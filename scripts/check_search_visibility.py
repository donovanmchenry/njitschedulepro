"""Check the public SEO release over HTTP using only the Python standard library."""

import argparse
from html.parser import HTMLParser
import json
from urllib.error import HTTPError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET


PRODUCTION = 'https://www.njitschedulepro.com'
PATHS = [
    '/',
    '/guides/njit-schedule-builder',
    '/guides/njit-schedule-around-work',
    '/guides/export-njit-schedule-to-google-calendar',
]


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.meta = {}
        self.canonicals = []
        self.headings = 0
        self.links = []
        self.title = ''
        self.in_title = False
        self.in_json = False
        self.json_text = ''
        self.structured_data = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'meta':
            self.meta[attrs.get('name') or attrs.get('property')] = attrs.get('content', '')
        if tag == 'link' and attrs.get('rel') == 'canonical':
            self.canonicals.append(attrs.get('href'))
        if tag == 'h1':
            self.headings += 1
        if tag == 'a':
            self.links.append(attrs.get('href', ''))
        if tag == 'title':
            self.in_title = True
        if tag == 'script' and attrs.get('type') == 'application/ld+json':
            self.in_json = True
            self.json_text = ''

    def handle_endtag(self, tag):
        if tag == 'title':
            self.in_title = False
        if tag == 'script' and self.in_json:
            self.structured_data.append(json.loads(self.json_text))
            self.in_json = False

    def handle_data(self, data):
        if self.in_title:
            self.title += data
        if self.in_json:
            self.json_text += data


def fetch(url):
    request = Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)',
    })
    with urlopen(request, timeout=30) as response:
        return response.read(), response.headers


def check(base_url, expected_origin):
    titles = set()
    descriptions = set()
    for path in PATHS:
        body, headers = fetch(urljoin(base_url, path))
        page = Page()
        html = body.decode('utf-8')
        page.feed(html)
        assert 'class="invisible"' not in html, (path, 'content hidden until JavaScript runs')
        canonical = urljoin(expected_origin, path)
        assert [value.rstrip('/') for value in page.canonicals] == [canonical.rstrip('/')], (path, 'canonical', page.canonicals)
        assert page.headings == 1, (path, 'h1 count', page.headings)
        assert page.title and page.title not in titles, (path, 'unique title')
        titles.add(page.title)
        description = page.meta.get('description', '')
        assert description and description not in descriptions, (path, 'unique description')
        descriptions.add(description)
        directives = ','.join([page.meta.get('robots', ''), page.meta.get('googlebot', ''), headers.get('X-Robots-Tag', '')]).lower()
        assert 'noindex' not in directives and 'nosnippet' not in directives, (path, directives)
        assert page.structured_data, (path, 'missing structured data')
        assert page.meta.get('og:image'), (path, 'missing social image')
        assert 'https://www.njit.edu/registrar/schedules' in page.links, (path, 'official source')
        if path == '/':
            for guide in PATHS[1:]:
                assert guide in page.links, ('missing guide link', guide)
            graph = page.structured_data[0]['@graph']
            assert {node['@type'] for node in graph} >= {'WebApplication', 'WebSite'}
        else:
            assert '/' in page.links, (path, 'missing builder link')
            assert page.structured_data[0]['@type'] == 'BreadcrumbList'
        image_url = page.meta['og:image']
        image_path = urlparse(image_url).path
        image_bytes, image_headers = fetch(urljoin(base_url, image_path))
        assert image_headers.get_content_type() == 'image/png' and image_bytes.startswith(b'\x89PNG'), image_url
        print(f'PASS {path}: indexable HTML, unique metadata, canonical, links, schema, social image')

    body, headers = fetch(urljoin(base_url, '/sitemap.xml'))
    root = ET.fromstring(body)
    locations = [node.text for node in root.findall('{*}url/{*}loc')]
    assert set(locations) == {urljoin(expected_origin, path) for path in PATHS}, locations
    print(f'PASS /sitemap.xml: {len(locations)} production URLs')

    body, headers = fetch(urljoin(base_url, '/robots.txt'))
    rules = body.decode('utf-8')
    assert 'User-Agent: *' in rules and 'Allow: /' in rules, rules
    assert 'Disallow: /\n' not in rules, rules
    assert f'Sitemap: {expected_origin}/sitemap.xml' in rules, rules
    print('PASS /robots.txt: public crawling allowed and sitemap advertised')

    try:
        fetch(urljoin(base_url, '/guides/this-guide-does-not-exist'))
    except HTTPError as error:
        assert error.code == 404, error.code
    else:
        raise AssertionError('Unknown guide must return HTTP 404')
    print('PASS unknown guide: HTTP 404')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', default=PRODUCTION)
    parser.add_argument('--expected-origin', default=PRODUCTION)
    args = parser.parse_args()
    check(args.base_url.rstrip('/') + '/', args.expected_origin.rstrip('/'))
