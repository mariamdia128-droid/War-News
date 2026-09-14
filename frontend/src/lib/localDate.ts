export const APP_TIME_ZONE = "Asia/Beirut";

export const getBeirutDate = (dayOffset = 0, now = new Date()): string => {
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone: APP_TIME_ZONE,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(now);
  const values = Object.fromEntries(parts.map((part) => [part.type, part.value]));
  const localCalendarDate = new Date(Date.UTC(
    Number(values.year),
    Number(values.month) - 1,
    Number(values.day) + dayOffset,
    12,
  ));
  return localCalendarDate.toISOString().slice(0, 10);
};

const isValidDateParts = (year: number, month: number, day: number) => {
  const date = new Date(Date.UTC(year, month - 1, day));
  return (
    date.getUTCFullYear() === year
    && date.getUTCMonth() === month - 1
    && date.getUTCDate() === day
  );
};

const toDateInputValue = (year: number, month: number, day: number) => {
  if (!isValidDateParts(year, month, day)) {
    return "";
  }
  return [
    String(year).padStart(4, "0"),
    String(month).padStart(2, "0"),
    String(day).padStart(2, "0"),
  ].join("-");
};

export const normalizeDateInputValue = (value: string | null | undefined): string => {
  const trimmed = value?.trim();
  if (!trimmed) {
    return "";
  }

  const isoMatch = /^(\d{4})-(\d{2})-(\d{2})$/.exec(trimmed);
  if (isoMatch) {
    return toDateInputValue(
      Number(isoMatch[1]),
      Number(isoMatch[2]),
      Number(isoMatch[3]),
    );
  }

  const slashMatch = /^(\d{1,2})\/(\d{1,2})\/(\d{4})$/.exec(trimmed);
  if (!slashMatch) {
    return "";
  }

  const first = Number(slashMatch[1]);
  const second = Number(slashMatch[2]);
  const year = Number(slashMatch[3]);
  const month = first > 12 ? second : first;
  const day = first > 12 ? first : second;
  return toDateInputValue(year, month, day);
};
