import { LogOut } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Logo } from "./logo";

export function TopBar({ onLogout }: { onLogout: () => void }) {
  return (
    <header className="sticky top-0 z-10 border-b border-line bg-canvas/85 backdrop-blur">
      <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-4 sm:px-6">
        <Logo />
        <Button variant="ghost" size="sm" icon={<LogOut className="size-4" />} onClick={onLogout}>
          Sign out
        </Button>
      </div>
    </header>
  );
}
