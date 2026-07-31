export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-background px-4">
      <div
        className="pointer-events-none absolute inset-0 opacity-40"
        style={{
          backgroundImage:
            "radial-gradient(600px circle at 20% 20%, hsl(var(--primary) / 0.18), transparent), radial-gradient(600px circle at 80% 80%, hsl(var(--primary) / 0.12), transparent)",
        }}
      />
      <div className="relative z-10 w-full max-w-sm">{children}</div>
    </div>
  );
}
