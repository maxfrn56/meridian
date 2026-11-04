export function PageFallback() {
  return (
    <div className="mx-auto max-w-6xl px-5 py-8">
      <div className="h-4 w-28 animate-pulse rounded bg-muted" />
      <div className="mt-3 h-9 w-64 animate-pulse rounded bg-muted" />
      <div className="mt-8 grid gap-4 md:grid-cols-4">
        {Array.from({ length: 4 }).map((_, index) => (
          <div key={index} className="h-28 animate-pulse rounded-xl bg-muted" />
        ))}
      </div>
      <div className="mt-4 h-72 animate-pulse rounded-xl bg-muted" />
    </div>
  );
}
