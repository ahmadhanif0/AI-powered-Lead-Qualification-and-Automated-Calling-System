/**
 * Reusable pagination component.
 *
 * Props:
 *   currentPage  – 1-based current page number
 *   totalPages   – total number of pages
 *   total        – total record count (for display)
 *   pageSize     – records per page (for display)
 *   onPageChange – (newPage: number) => void
 */
export function Pagination({ currentPage, totalPages, total, pageSize, onPageChange }) {
  if (totalPages <= 1) return null;

  // Build page number list with ellipsis
  function getPages() {
    const pages = [];
    const delta = 2; // pages around current

    for (let i = 1; i <= totalPages; i++) {
      if (
        i === 1 ||
        i === totalPages ||
        (i >= currentPage - delta && i <= currentPage + delta)
      ) {
        pages.push(i);
      } else if (pages[pages.length - 1] !== "…") {
        pages.push("…");
      }
    }
    return pages;
  }

  const from = (currentPage - 1) * pageSize + 1;
  const to   = Math.min(currentPage * pageSize, total);

  return (
    <div className="flex items-center justify-between px-3 py-3 border-t border-gray-800 text-xs text-gray-400">
      {/* Record count */}
      <span>
        {total > 0 ? `${from}–${to} of ${total}` : "0 results"}
      </span>

      {/* Page buttons */}
      <div className="flex items-center gap-1">
        {/* Prev */}
        <button
          onClick={() => onPageChange(currentPage - 1)}
          disabled={currentPage === 1}
          className="px-2 py-1 rounded bg-gray-800 hover:bg-gray-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        >
          ←
        </button>

        {/* Page numbers */}
        {getPages().map((p, i) =>
          p === "…" ? (
            <span key={`ellipsis-${i}`} className="px-1 text-gray-600">…</span>
          ) : (
            <button
              key={p}
              onClick={() => onPageChange(p)}
              className={`w-7 h-7 rounded transition-colors ${
                p === currentPage
                  ? "bg-blue-600 text-white font-medium"
                  : "bg-gray-800 hover:bg-gray-700"
              }`}
            >
              {p}
            </button>
          )
        )}

        {/* Next */}
        <button
          onClick={() => onPageChange(currentPage + 1)}
          disabled={currentPage === totalPages}
          className="px-2 py-1 rounded bg-gray-800 hover:bg-gray-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        >
          →
        </button>
      </div>

      {/* Page X of Y */}
      <span className="text-gray-600">
        Page {currentPage} of {totalPages}
      </span>
    </div>
  );
}
