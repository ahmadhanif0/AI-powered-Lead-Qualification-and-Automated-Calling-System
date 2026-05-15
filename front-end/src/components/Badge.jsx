const VARIANTS = {
  green:  "bg-green-900  text-green-300",
  red:    "bg-red-900    text-red-300",
  yellow: "bg-yellow-900 text-yellow-300",
  blue:   "bg-blue-900   text-blue-300",
  orange: "bg-orange-900 text-orange-300",
  gray:   "bg-gray-700   text-gray-300",
};

export function Badge({ children, variant = "gray" }) {
  return (
    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${VARIANTS[variant] || VARIANTS.gray}`}>
      {children}
    </span>
  );
}
