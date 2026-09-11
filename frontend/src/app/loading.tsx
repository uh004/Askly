import { LoaderCircle } from "lucide-react";

export default function Loading() {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center">
      <LoaderCircle className="animate-spin text-blue-600" size={36} />
      <p className="mt-4 text-sm font-semibold text-slate-500">화면을 준비하고 있습니다...</p>
    </div>
  );
}
