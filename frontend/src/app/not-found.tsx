import { SearchX } from "lucide-react";
import Link from "next/link";

export default function NotFound() {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center text-center">
      <SearchX className="text-slate-300" size={48} />
      <h1 className="mt-5 text-2xl font-black">페이지를 찾을 수 없습니다.</h1>
      <Link
        href="/"
        className="mt-6 rounded-xl bg-blue-600 px-5 py-3 text-sm font-bold text-white"
      >
        대시보드로 이동
      </Link>
    </div>
  );
}
