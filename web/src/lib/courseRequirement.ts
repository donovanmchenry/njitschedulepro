export interface ElectiveRequirement {
  departments: string[];
  minimumLevel: number;
  courseCount?: number;
}

const DEPARTMENT_GROUP = '[A-Z]{2,5}(?:\\s*\\/\\s*[A-Z]{2,5})*';

export function parseElectiveRequirement(query: string): ElectiveRequirement | null {
  const normalized = query.trim().replace(/\s+/g, ' ').toUpperCase();
  const match = normalized.match(
    new RegExp(`^(${DEPARTMENT_GROUP})\\s+ELECTIVES?\\s+(\\d{3,4})(.*)$`)
  );
  if (!match) return null;

  const tail = match[3].trim();
  const tailMatch = tail.match(
    /^(?:(?:(?:OR|AND)\s+)?(?:ABOVE|HIGHER)|\+)?(?:\s*(\d+))?$/
  );
  if (!tailMatch) return null;

  const courseCount = tailMatch[1] ? Number(tailMatch[1]) : undefined;
  if (courseCount != null && (courseCount < 1 || courseCount > 20)) return null;

  return {
    departments: match[1].split('/').map((department) => department.trim()),
    minimumLevel: Number(match[2]),
    courseCount,
  };
}

export function getCourseKeyParts(courseKey: string): {
  department: string;
  number: number;
} | null {
  const match = courseKey.trim().toUpperCase().match(/^([A-Z]{2,5})\s*(\d{3,4})/);
  if (!match) return null;
  return { department: match[1], number: Number(match[2]) };
}

export function courseMatchesRequirement(
  courseKey: string,
  requirement: ElectiveRequirement
): boolean {
  const parts = getCourseKeyParts(courseKey);
  return Boolean(
    parts &&
    requirement.departments.includes(parts.department) &&
    parts.number >= requirement.minimumLevel
  );
}

export function formatRequirementLabel(requirement: ElectiveRequirement): string {
  const base = `${requirement.departments.join('/')} electives · ${requirement.minimumLevel}+`;
  return requirement.courseCount ? `${base} · choose ${requirement.courseCount}` : base;
}
