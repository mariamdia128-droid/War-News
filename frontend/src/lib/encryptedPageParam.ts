const PAGE_TOKEN_PREFIX = "pg:";

const toBase64Url = (value: string) =>
  btoa(value).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");

const fromBase64Url = (value: string) => {
  const normalized = value.replace(/-/g, "+").replace(/_/g, "/");
  const padded = normalized.padEnd(normalized.length + ((4 - (normalized.length % 4)) % 4), "=");
  return atob(padded);
};

export const encodePageParam = (page: number) => {
  const normalizedPage = Math.max(1, Math.floor(page));
  return toBase64Url(`${PAGE_TOKEN_PREFIX}${normalizedPage}`);
};

export const decodePageParam = (value: string | null) => {
  if (!value) {
    return 1;
  }

  const legacyPage = Number(value);
  if (Number.isInteger(legacyPage) && legacyPage > 0) {
    return legacyPage;
  }

  try {
    const decoded = fromBase64Url(value);
    if (!decoded.startsWith(PAGE_TOKEN_PREFIX)) {
      return 1;
    }
    const page = Number(decoded.slice(PAGE_TOKEN_PREFIX.length));
    return Number.isInteger(page) && page > 0 ? page : 1;
  } catch {
    return 1;
  }
};
