import { useEffect } from "react";
import { X, AlertTriangle } from "lucide-react";
import { Spinner } from "./Spinner";

/**
 * Reusable delete confirmation modal.
 *
 * Props:
 *   open       – boolean
 *   onClose    – () => void
 *   onConfirm  – () => void  (async ok)
 *   title      – string
 *   itemName   – string  (shown in a highlighted box)
 *   warning    – string  (optional extra warning line)
 *   isDeleting – boolean (shows spinner on confirm button)
 */
export function DeleteConfirmModal({
  open,
  onClose,
  onConfirm,
  title      = "Delete",
  itemName   = "",
  warning    = "This action cannot be undone.",
  isDeleting = false,
}) {
  // Close on Escape
  useEffect(() => {
    if (!open) return;
    const handler = (e) => { if (e.key === "Escape" && !isDeleting) onClose(); };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [open, onClose, isDeleting]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4"
      onClick={(e) => { if (e.target === e.currentTarget && !isDeleting) onClose(); }}
    >
      <div className="bg-gray-900 border border-gray-700 rounded-xl w-full max-w-md shadow-2xl">

        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-gray-800">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-full bg-red-900/50 flex items-center justify-center shrink-0">
              <AlertTriangle size={18} className="text-red-400" />
            </div>
            <h2 className="font-bold text-white text-base">{title}</h2>
          </div>
          <button
            onClick={onClose}
            disabled={isDeleting}
            className="text-gray-500 hover:text-white transition-colors disabled:opacity-40"
          >
            <X size={18} />
          </button>
        </div>

        {/* Body */}
        <div className="p-5 space-y-4">
          <p className="text-gray-300 text-sm">
            Are you sure you want to delete this item? This will remove it permanently.
          </p>

          {/* Item name highlight */}
          {itemName && (
            <div className="bg-gray-800 border border-gray-700 rounded-lg px-4 py-3">
              <span className="text-xs text-gray-500 block mb-0.5">Item</span>
              <span className="text-white font-semibold text-sm">{itemName}</span>
            </div>
          )}

          {/* Warning box */}
          <div className="flex items-start gap-2 bg-amber-900/20 border border-amber-800/50 rounded-lg p-3">
            <AlertTriangle size={14} className="text-amber-400 shrink-0 mt-0.5" />
            <p className="text-amber-300 text-xs leading-relaxed">{warning}</p>
          </div>
        </div>

        {/* Footer */}
        <div className="flex gap-3 p-5 border-t border-gray-800">
          <button
            onClick={onClose}
            disabled={isDeleting}
            className="flex-1 py-2 rounded-lg bg-gray-700 hover:bg-gray-600 disabled:opacity-40 text-sm transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            disabled={isDeleting}
            className="flex-1 py-2 rounded-lg bg-red-600 hover:bg-red-500 disabled:opacity-50 text-sm font-medium transition-colors flex items-center justify-center gap-2"
          >
            {isDeleting ? (
              <>
                <Spinner size={14} />
                Deleting…
              </>
            ) : (
              "Delete"
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
