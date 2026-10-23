"""Semester dates used when exporting a generated class schedule."""

# First and last class days, from NJIT's official Spring 2027 academic calendar:
# https://www.njit.edu/registrar/spring-2027-academic-calendar
SPRING_2027_TERM = '202710'
SPRING_2027_DATES = ('2027-01-19', '2027-05-03')


def schedule_term_dates(terms: set[str]) -> tuple[str, str]:
    if terms == {SPRING_2027_TERM}:
        return SPRING_2027_DATES
    # Preserve exports of existing Fall plans and schedules without a term.
    if not terms or terms == {'202690'}:
        return '2026-09-01', '2026-12-13'
    raise ValueError('Supply explicit semester dates for this schedule; do not mix semesters.')
