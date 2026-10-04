import { Upload } from "lucide-react";
import { type ChangeEvent, useRef } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { errorMessage } from "@/lib/api";
import { parseCsv } from "@/lib/csv";
import type { Sections } from "@/lib/types";

export function CsvUploadButton({ onLoad }: { onLoad: (sections: Sections) => void }) {
  const input = useRef<HTMLInputElement>(null);

  const handleFile = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    try {
      onLoad(parseCsv(await file.text()));
      toast.success(`Loaded ${file.name}`);
    } catch (error) {
      toast.error(errorMessage(error));
    }
  };

  return (
    <>
      <input ref={input} type="file" accept=".csv,text/csv" className="hidden" onChange={handleFile} />
      <Button size="sm" icon={<Upload className="size-3.5" />} onClick={() => input.current?.click()}>
        Upload CSV
      </Button>
    </>
  );
}
