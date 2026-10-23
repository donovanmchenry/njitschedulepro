"""Export NJIT's anonymous Banner registration search as the existing CSV format."""

import argparse
import csv
import json
import time
import uuid
from html import unescape
from collections import defaultdict
from datetime import datetime
from http.cookiejar import CookieJar
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import HTTPCookieProcessor, Request, build_opener

BASE = 'https://reg-prod.ec.njit.edu/StudentRegistrationSsb/ssb/'
FIELDS = ['Term', 'Course', 'Title', 'Section', 'CRN', 'Days', 'Times', 'Location',
          'Status', 'Max', 'Now', 'Instructor', 'Delivery Mode', 'Credits', 'Info', 'Comments']
DAYS = [('monday', 'M'), ('tuesday', 'T'), ('wednesday', 'W'), ('thursday', 'R'),
        ('friday', 'F'), ('saturday', 'S'), ('sunday', 'U')]


def clock_time(value):
    return datetime.strptime(value, '%H%M').strftime('%I:%M %p').lstrip('0') if value else ''


def section_rows(section):
    """Preserve every meeting; the API normalizer merges repeated CRNs."""
    attributes = [a['description'] for a in section.get('sectionAttributes', [])]
    delivery = section.get('instructionalMethodDescription') or next(
        (a for a in attributes if any(k in a.lower() for k in ('face', 'online', 'hybrid', 'async', 'distance'))), '')
    status = 'Open' if section['openSection'] else 'Closed'
    base = {
        'Term': section['term'], 'Course': f"{section['subject']} {section['courseNumber']}",
        'Title': unescape(section['courseTitle']), 'Section': section['sequenceNumber'],
        'CRN': section['courseReferenceNumber'], 'Status': status,
        'Max': section.get('maximumEnrollment'), 'Now': section.get('enrollment'),
        'Instructor': '; '.join(f['displayName'] for f in section.get('faculty', [])),
        'Delivery Mode': delivery,
        'Credits': section.get('creditHours') if section.get('creditHours') is not None else section.get('creditHourLow'),
        'Info': '', 'Comments': '',
    }
    for meeting in section.get('meetingsFaculty') or [{'meetingTime': {}}]:
        m = meeting['meetingTime']
        start, end = clock_time(m.get('beginTime')), clock_time(m.get('endTime'))
        yield {**base, 'Days': ''.join(code for day, code in DAYS if m.get(day)),
               'Times': f'{start} - {end}' if start and end else '',
               'Location': ' '.join(str(v) for v in (m.get('building'), m.get('room')) if v)}


def validate_page(page, term, expected_total=None):
    if not page.get('success') or not isinstance(page.get('data'), list):
        raise ValueError('NJIT registration search did not return a successful results page')
    total = page.get('totalCount')
    if not isinstance(total, int) or total <= 0 or (expected_total is not None and total != expected_total):
        raise ValueError('Catalog count is empty or changed during pagination; retry the complete import')
    if any(s.get('term') != term or not s.get('courseReferenceNumber') for s in page['data']):
        raise ValueError('NJIT returned an invalid section or a different semester')
    return total


def fetch_sections(term):
    session = build_opener(HTTPCookieProcessor(CookieJar()))
    session_id = str(uuid.uuid4())

    def request(path, params=None, post=False):
        encoded = urlencode(params or {}).encode()
        url = BASE + path + (('?' + encoded.decode()) if encoded and not post else '')
        for attempt in range(3):
            try:
                with session.open(Request(url, data=encoded if post else None), timeout=60) as response:
                    return response.read()
            except Exception:
                if attempt == 2:
                    raise
                time.sleep(3 * (attempt + 1))

    request('term/termSelection?mode=search')
    selected = json.loads(request('term/search?mode=search', {'term': term, 'uniqueSessionId': session_id}, post=True))
    if 'classSearch' not in selected.get('fwdURL', ''):
        raise ValueError('NJIT did not accept the public class-search semester')
    sections, total = [], None
    while total is None or len(sections) < total:
        page = json.loads(request('searchResults/searchResults', {
            'txt_term': term, 'startDatepicker': '', 'endDatepicker': '',
            'pageOffset': len(sections), 'pageMaxSize': 500,
            'sortColumn': 'subjectDescription', 'sortDirection': 'asc',
            'uniqueSessionId': session_id,
        }))
        total = validate_page(page, term, total)
        if not page['data']:
            raise ValueError('NJIT ended the catalog before all sections were downloaded')
        sections.extend(page['data'])
        print(f'Downloaded {len(sections)}/{total} {term} sections', flush=True)
    if len(sections) != total or len({s['courseReferenceNumber'] for s in sections}) != total:
        raise ValueError('Incomplete or duplicated registration catalog; refusing to publish')
    return sections


def write_catalog(sections, directory):
    grouped = defaultdict(list)
    for section in sections:
        grouped[section['subject']].extend(section_rows(section))
    directory.mkdir(parents=True, exist_ok=True)
    # Conversion and complete-catalog validation finish before existing files are touched.
    for old in directory.glob('*.csv'):
        old.unlink()
    term = sections[0]['term']
    for subject, rows in sorted(grouped.items()):
        path = directory / f'Course_Schedule_{term}_{subject}_Registration.csv'
        with path.open('w', newline='', encoding='utf-8') as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(rows)
    (directory / '_update_metadata.txt').write_text(
        f'Last Updated: {datetime.now().isoformat()}\nTerm: {term}\n'
        f'Sections: {len(sections)}\nSubjects: {len(grouped)}\n'
        'Update Method: NJIT public registration search API\n')
    print(f'Published {len(sections)} sections across {len(grouped)} subjects', flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--term', required=True)
    parser.add_argument('--catalog-dir', type=Path, default=Path('courseschedules'))
    args = parser.parse_args()
    if not (args.term.isdigit() and len(args.term) == 6):
        parser.error('term must be a six-digit Banner code')
    write_catalog(fetch_sections(args.term), args.catalog_dir)


if __name__ == '__main__':
    main()
