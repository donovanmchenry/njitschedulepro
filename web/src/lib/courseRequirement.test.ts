import { describe, expect, it } from 'vitest';
import {
  courseMatchesRequirement,
  formatRequirementLabel,
  parseElectiveRequirement,
} from './courseRequirement';

describe('elective requirement search', () => {
  it('parses a single-department requirement with a course count', () => {
    expect(parseElectiveRequirement('CS Elective 300 or above 2')).toEqual({
      departments: ['CS'],
      minimumLevel: 300,
      courseCount: 2,
    });
  });

  it('parses a multi-department requirement', () => {
    const requirement = parseElectiveRequirement(
      'CS/IS/IT/DS Elective 300 or above'
    );

    expect(requirement).toEqual({
      departments: ['CS', 'IS', 'IT', 'DS'],
      minimumLevel: 300,
      courseCount: undefined,
    });
    expect(requirement && courseMatchesRequirement('IT 310', requirement)).toBe(true);
    expect(requirement && courseMatchesRequirement('CS 288', requirement)).toBe(false);
    expect(requirement && courseMatchesRequirement('MATH 333', requirement)).toBe(false);
  });

  it('supports compact requirement syntax and rejects unrelated searches', () => {
    const requirement = parseElectiveRequirement('cs/is electives 400+ 1');
    expect(requirement).toEqual({
      departments: ['CS', 'IS'],
      minimumLevel: 400,
      courseCount: 1,
    });
    expect(requirement && formatRequirementLabel(requirement)).toBe(
      'CS/IS electives · 400+ · choose 1'
    );
    expect(parseElectiveRequirement('CS 300')).toBeNull();
    expect(parseElectiveRequirement('CS elective sometime')).toBeNull();
  });
});
