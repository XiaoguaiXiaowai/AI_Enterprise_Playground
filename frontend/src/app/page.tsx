export default function HomePage() {
  return (
    <main className="mx-auto max-w-3xl px-6 py-16">
      <h1 className="text-3xl font-semibold">AI Enterprise Playground</h1>
      <p className="mt-4 text-sm text-muted-foreground">
        Backend: http://localhost:8000/docs
      </p>
      <div className="mt-6">
        <a className="text-sm text-slate-700 underline" href="/dashboard">
          Open Dashboard
        </a>
      </div>
    </main>
  );
}
