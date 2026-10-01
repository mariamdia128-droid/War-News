export const DuplicateBadge = ({ isDuplicate }: { isDuplicate: boolean }) => (
  isDuplicate ? (
    <span className="inline-flex rounded bg-amber-50 px-2 py-1 text-xs font-medium text-amber-700">
      Possible duplicate
    </span>
  ) : null
);
