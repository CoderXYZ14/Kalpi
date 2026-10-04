import { ArrowRight } from "lucide-react";
import { type FormEvent, useState } from "react";
import { Logo } from "@/components/layout/logo";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { errorMessage } from "@/lib/api";

interface LoginScreenProps {
  onLogin: (username: string, password: string) => Promise<void>;
}

export function LoginScreen({ onLogin }: LoginScreenProps) {
  const [username, setUsername] = useState("demo");
  const [password, setPassword] = useState("demo1234");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setError("");
    setLoading(true);
    try {
      await onLogin(username, password);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="grid min-h-screen place-items-center px-4">
      <div className="w-full max-w-sm animate-rise">
        <Logo />
        <h1 className="mt-8 text-2xl font-semibold tracking-tight">Sign in</h1>
        <p className="mt-1 text-sm text-ink-2">Execute a target portfolio on your broker in one click.</p>

        <form onSubmit={submit} className="mt-6 grid gap-4">
          <Field label="Username" htmlFor="username">
            <Input id="username" value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" required />
          </Field>
          <Field label="Password" htmlFor="password">
            <Input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              required
            />
          </Field>
          {error && <p className="rounded-lg bg-down-soft px-3 py-2 text-[13px] text-down">{error}</p>}
          <Button type="submit" variant="primary" size="lg" loading={loading} className="mt-1">
            Continue <ArrowRight className="size-4" />
          </Button>
        </form>

        <p className="mt-6 text-center text-[12px] text-ink-3">
          Demo account <span className="font-mono text-ink-2">demo / demo1234</span>
        </p>
      </div>
    </main>
  );
}
