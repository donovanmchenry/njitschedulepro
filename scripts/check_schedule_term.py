"""Verify the live browser catalog, API, solver, and calendar export agree on Spring 2027."""

import json
from urllib.request import Request, urlopen


SITE = 'https://www.njitschedulepro.com'
API = 'https://njitschedulepro.onrender.com'
TERM = '202710'


def read(url, payload=None):
    request = Request(url, data=json.dumps(payload).encode() if payload is not None else None,
                      headers={'Content-Type': 'application/json', 'Cache-Control': 'no-cache'})
    with urlopen(request, timeout=60) as response:
        body = response.read()
        return json.loads(body) if 'json' in response.headers.get('Content-Type', '') else body


def main():
    index = read(SITE + '/catalog/index.json')
    assert index.get('term') == TERM, ('frontend semester', index.get('term'))
    catalog = read(API + '/catalog?limit=10000')
    offerings = catalog['offerings']
    assert offerings and len(offerings) == catalog['total'], 'incomplete API catalog'
    assert {o['term'] for o in offerings} == {TERM}, 'wrong or mixed API semesters'
    assert {c['course_key'] for c in index['courses']} == {o['course_key'] for o in offerings}, 'frontend and API course lists differ'
    # Export data can repeat a section once for each meeting; compare unique CRNs.
    assert sum(c['section_count'] for c in index['courses']) == len({o['crn'] for o in offerings}), 'frontend and API section counts differ'
    print(f'PASS Spring 2027 catalog: {index["total"]} courses, {len({o["crn"] for o in offerings})} sections')
    course = next(o['course_key'] for o in offerings if o['course_key'] == 'CS 114' and o['status'] == 'Open' and o['meetings'])
    solved = read(API + '/solve', {'term': TERM, 'required_course_keys': [course], 'max_results': 1})
    assert solved['schedules'], 'no schedule generated'
    schedule = solved['schedules'][0]
    assert {o['term'] for o in schedule['offerings']} == {TERM}, 'solver returned another semester'
    print(f'PASS Spring 2027 schedule generation: {course}')
    calendar = read(API + '/export/ics', schedule).decode()
    assert 'DTSTART:2027' in calendar and 'UNTIL=20270503T235959' in calendar, 'calendar has wrong semester dates'
    print('PASS calendar export: January–May 2027')


if __name__ == '__main__':
    main()
