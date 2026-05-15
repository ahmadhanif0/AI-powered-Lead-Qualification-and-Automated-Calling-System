// Shared colour/label helpers used across multiple pages

export function leadStatusColor(status) {
  switch (status) {
    case "Booked":          return "text-green-400";
    case "Won't Follow Up": return "text-orange-400";
    case "Pending":         return "text-yellow-400";
    case "Rejected":        return "text-red-400";
    default:                return "text-gray-500";
  }
}

export function callStatusColor(status) {
  switch (status) {
    case "completed":         return "text-green-400";
    case "calling":           return "text-yellow-400";
    case "call_not_attended": return "text-orange-400";
    case "call_rejected":     return "text-red-400";
    case "call_later":        return "text-blue-400";
    case "wrong_number":      return "text-red-500";
    default:                  return "text-gray-400";
  }
}

export function callStatusLabel(status) {
  const map = {
    pending:            "Pending",
    calling:            "Calling…",
    completed:          "Completed",
    call_not_attended:  "Not Answered",
    call_rejected:      "Rejected",
    call_later:         "Call Later",
    wrong_number:       "Wrong Number",
  };
  return map[status] || status || "—";
}

export function decisionColor(decision) {
  switch ((decision || "").toLowerCase()) {
    case "interested":     return "text-green-400";
    case "not interested": return "text-red-400";
    case "call later":     return "text-blue-400";
    case "wrong number":   return "text-red-500";
    case "no response":    return "text-gray-400";
    default:               return "text-gray-500";
  }
}

export function formatRetryTime(isoString) {
  if (!isoString) return "—";
  const retryAt = new Date(isoString);
  const diffMs  = retryAt - Date.now();
  const absSec  = Math.round(Math.abs(diffMs) / 1000);
  const mins    = Math.floor(absSec / 60);
  const secs    = absSec % 60;
  if (diffMs > 0) return mins > 0 ? `in ${mins}m ${secs}s` : `in ${secs}s`;
  return mins > 0 ? `${mins}m ago (overdue)` : `${secs}s ago (overdue)`;
}
