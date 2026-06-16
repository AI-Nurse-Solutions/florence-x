export function LiveDot({ connected }: { connected: boolean }) {
  return (
    <span className="inline-flex items-center gap-1.5 text-xs text-gray-500">
      <span
        className={`h-2 w-2 rounded-full ${connected ? "bg-emerald-500" : "bg-gray-300"}`}
        aria-hidden
      />
      {connected ? "live" : "offline"}
    </span>
  );
}
