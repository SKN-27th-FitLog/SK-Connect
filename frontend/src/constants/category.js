export const CATEGORY_OPTIONS = [
  { label: "운동", value: "WORKOUT" },
  { label: "식단", value: "DIET" },
  { label: "자유", value: "FREE" },
  { label: "질문", value: "QUESTION" },
  { label: "스터디", value: "STUDY" },
];

export const CATEGORY_LABELS = CATEGORY_OPTIONS.map((item) => item.label);

export const findCategoryByLabel = (label) =>
  CATEGORY_OPTIONS.find((item) => item.label === label);

export const findCategoryByValue = (value) =>
  CATEGORY_OPTIONS.find((item) => item.value === value);