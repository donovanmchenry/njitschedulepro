import unittest

from scraper.registration_catalog import section_rows, validate_page


class RegistrationCatalogTests(unittest.TestCase):
    def section(self):
        return {'term': '202710', 'courseReferenceNumber': '11712', 'subject': 'CS',
                'courseNumber': '100', 'sequenceNumber': '002', 'courseTitle': 'Computing &amp; Science',
                'openSection': True, 'maximumEnrollment': 60, 'enrollment': 0,
                'creditHours': None, 'creditHourLow': 3,
                'faculty': [{'displayName': 'Test, Professor'}],
                'sectionAttributes': [{'description': 'Face-To-Face'}],
                'meetingsFaculty': [{'meetingTime': {'monday': True, 'thursday': True,
                    'beginTime': '1000', 'endTime': '1120', 'building': 'CKB', 'room': '204'}},
                    {'meetingTime': {'tuesday': True, 'beginTime': '1200', 'endTime': '1250'}}]}

    def test_preserves_multiple_meetings_and_registration_metadata(self):
        rows = list(section_rows(self.section()))
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]['Days'], 'MR')
        self.assertEqual(rows[0]['Times'], '10:00 AM - 11:20 AM')
        self.assertEqual(rows[1]['Times'], '12:00 PM - 12:50 PM')
        self.assertEqual(rows[0]['Location'], 'CKB 204')
        self.assertEqual(rows[0]['Credits'], 3)
        self.assertEqual(rows[0]['Now'], 0)
        self.assertEqual(rows[0]['CRN'], rows[1]['CRN'])
        self.assertEqual(rows[0]['Delivery Mode'], 'Face-To-Face')
        self.assertEqual(rows[0]['Title'], 'Computing & Science')

    def test_asynchronous_section_is_kept_without_inventing_meetings(self):
        section = self.section()
        section.update(meetingsFaculty=[], openSection=False,
                       instructionalMethodDescription='Online Asynchronous')
        row, = section_rows(section)
        self.assertEqual(row['Days'], '')
        self.assertEqual(row['Times'], '')
        self.assertEqual(row['Status'], 'Closed')
        self.assertEqual(row['Delivery Mode'], 'Online Asynchronous')

    def test_rejects_wrong_semester_and_changing_page_counts(self):
        page = {'success': True, 'totalCount': 5744, 'data': [self.section()]}
        self.assertEqual(validate_page(page, '202710'), 5744)
        with self.assertRaises(ValueError):
            validate_page(page, '202695')
        with self.assertRaises(ValueError):
            validate_page(page, '202710', 5743)
        with self.assertRaises(ValueError):
            validate_page({'success': False}, '202710')


if __name__ == '__main__':
    unittest.main()
