"use client";

interface SkipToContentProps {
  targetId?: string;
  label?: string;
}

export function SkipToContent({
  targetId = "main-content",
  label = "Skip to main content",
}: SkipToContentProps) {
  const handleClick = (e: React.MouseEvent<HTMLAnchorElement>) => {
    e.preventDefault();
    const target = document.getElementById(targetId);
    if (target) {
      target.setAttribute("tabindex", "-1");
      target.focus();
      target.scrollIntoView({ behavior: "smooth" });
    }
  };

  return (
    <a
      href={`#${targetId}`}
      onClick={handleClick}
      className="sr-only focus:not-sr-only focus:fixed focus:top-4 focus:left-4 focus:z-[100] focus:px-4 focus:py-2.5 focus:bg-emerald-400 focus:text-slate-950 focus:font-bold focus:text-xs focus:rounded-lg focus:shadow-2xl focus:ring-4 focus:ring-emerald-500/50 focus:outline-none transition-transform"
    >
      {label}
    </a>
  );
}
