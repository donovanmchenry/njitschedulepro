export const guides = [
  {
    slug: 'njit-schedule-builder',
    title: 'How to build an NJIT class schedule',
    description: 'Build an NJIT class schedule by selecting courses, setting your availability, and comparing conflict-free section combinations in NJIT Schedule Pro.',
    intro: 'NJIT Schedule Pro generates class schedules from your selected courses and availability. Instead of trying every section combination yourself, choose your courses and compare the schedules that fit.',
    steps: [
      ['Choose your courses', 'Search by course code or title and add the courses you want to take. Check your degree requirements with your advisor or DegreeWorks before choosing courses.'],
      ['Set your availability and filters', 'Use Times to avoid to block hours when you cannot attend class. Set credit limits, section availability, class type, and first or last class times in Options.'],
      ['Generate and compare schedules', 'Select Show schedules, review the weekly calendar, and choose Save on options you want to compare in the Saved tab. If there are no results, relax a filter or try another course combination.'],
      ['Register through NJIT', 'Use your chosen schedule as a planning reference. NJIT Schedule Pro does not enroll you in classes. Verify sections and availability in NJIT’s official registration system.'],
    ],
  },
  {
    slug: 'njit-schedule-around-work',
    title: 'Plan your NJIT class schedule around work and commuting',
    description: 'Use unavailable time blocks in NJIT Schedule Pro to find class schedules that fit your work shifts, commute, and other commitments.',
    intro: 'To plan NJIT classes around a job, enter your work hours as unavailable time blocks before generating schedules. Add travel time too: a class that finishes exactly when a shift starts may not leave enough time to get there.',
    steps: [
      ['Block each commitment', 'Add unavailable time blocks for each day you work. For example, if you work Monday from 2 p.m. to 6 p.m., block that interval plus the commute time you need.'],
      ['Choose courses and delivery modes', 'Add your required courses, then use delivery mode filters if you need online or hybrid sections. Review meeting details rather than assuming an online class has no scheduled meetings.'],
      ['Compare gaps between classes', 'Choose Show schedules and inspect the weekly calendar. Set Longest break between classes in Options to limit gaps when you want a more compact day on campus.'],
      ['Adjust when no schedule fits', 'Try different sections, a different elective, or fewer constraints. Keep actual work commitments blocked, and discuss changes to your course plan with your advisor.'],
    ],
  },
  {
    slug: 'export-njit-schedule-to-google-calendar',
    title: 'Export your NJIT class schedule to Google Calendar',
    description: 'Download your NJIT Schedule Pro plan as an ICS calendar file and import it into Google Calendar to keep class times alongside your other commitments.',
    intro: 'NJIT Schedule Pro can export a selected schedule as an ICS calendar file. You can import that file into Google Calendar or another calendar application that supports ICS.',
    steps: [
      ['Select your schedule', 'Generate schedules and select the plan you want to export. Verify its course sections and meeting times against your registered classes.'],
      ['Download the ICS file', 'Use the calendar export option to download an .ics file. Check the semester dates used for the export.'],
      ['Import into Google Calendar', 'In Google Calendar on a computer, open Settings, then Import & export. Select the downloaded ICS file and the destination calendar, then import it.'],
      ['Review imported events', 'Check dates, times, and time zones. A downloaded file is a snapshot, not a live subscription: changes to your classes will not automatically update imported events. Remove old events before importing a replacement to avoid duplicates.'],
    ],
  },
] as const;

export const schedulingFaqs = [
  ['What is NJIT Schedule Pro?', 'NJIT Schedule Pro is an independent course schedule builder for New Jersey Institute of Technology students. It generates conflict-free section combinations using selected courses, unavailable times, and filters.'],
  ['Does NJIT Schedule Pro register me for classes?', 'No. It helps you plan a schedule. Register through NJIT’s official system and verify course availability, prerequisites, and degree requirements there.'],
  ['Can I avoid classes during my work hours?', 'Yes. Add your work hours and any necessary travel time as unavailable time blocks before generating schedules.'],
  ['Can I export my schedule?', 'Yes. You can download a schedule as an ICS calendar file or CSV. Calendar exports are snapshots and do not automatically reflect later course changes.'],
  ['Is this the official NJIT schedule builder?', 'No. NJIT Schedule Pro is independently maintained by Donovan McHenry and is not affiliated with or endorsed by NJIT. Use official NJIT resources to confirm your registration details.'],
] as const;
