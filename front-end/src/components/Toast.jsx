import { useEffect } from "react";
import { CheckCircle, XCircle, X } from "lucide-react";

export function Toast({ message, type = "success", onClose }) {
  useEffect(() => {
    const t = setTimeout(onClose, 4000);
    return () => clearTimeout(t);
  }, [onClose]);

  const isSuccess = type === "success";

  return (
    <div className={`fixed bottom-6 right-6 z-50 flex items-center gap-3 px-4 py-3 rounded-lg shadow-xl border text-sm
      ${isSuccess
        ? "bg-green-900 border-green-700 text-green-200"
        : "bg-red-900 border-red-700 text-red-200"
      }`}
    >
      {isSuccess
        ? <CheckCircle size={16} className="text-green-400 shrink-0" />
        : <XCircle    size={16} className="text-red-400 shrink-0" />
      }
      <span>{message}</span>
      <button onClick={onClose} className="ml-2 opacity-60 hover:opacity-100">
        <X size={14} />
      </button>
    </div>
  );
}

// Simple hook to manage a single toast
import { useState, useCallback } from "react";

export function useToast() {
  const [toast, setToast] = useState(null);

  const show = useCallback((message, type = "success") => {
    setToast({ message, type });
  }, []);

  const hide = useCallback(() => setToast(null), []);

  const ToastEl = toast
    ? <Toast message={toast.message} type={toast.type} onClose={hide} />
    : null;

  return { show, ToastEl };
}
