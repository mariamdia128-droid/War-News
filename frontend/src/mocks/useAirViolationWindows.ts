import type { AirViolationWindowListResponse } from "../features/airViolations/types";

const mockWindows: AirViolationWindowListResponse = {
  items: [
    {
      id: "Sour:2026-09-17T10:00:00",
      caza_en: "Sour",
      caza_ar: "صور",
      window_start: "2026-09-17T10:00:00",
      window_end: "2026-09-17T10:42:00",
      violation_count: 4,
      villages: ["Naqoura", "Aalma ech Chaab"],
    },
  ],
  total: 1,
  limit: 25,
  offset: 0,
};

export const useAirViolationWindows = () => ({
  data: mockWindows,
  isLoading: false,
  isError: false,
});
