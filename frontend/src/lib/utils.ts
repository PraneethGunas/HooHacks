export function cn(...classes: Array<string | false | null | undefined>) {
  return classes.filter(Boolean).join(" ");
}

export function formatSats(value: number) {
  return `${Intl.NumberFormat("en-US").format(value)} sats`;
}

export function formatDuration(ms: number) {
  return `${(ms / 1000).toFixed(1)}s`;
}

export function truncate(text: string, max = 80) {
  if (text.length <= max) {
    return text;
  }

  return `${text.slice(0, max - 1)}...`;
}

export function confidenceOrder(value: "EMPIRICAL" | "THEORETICAL" | "SPECULATIVE") {
  if (value === "EMPIRICAL") {
    return 0;
  }
  if (value === "THEORETICAL") {
    return 1;
  }
  return 2;
}

export function titleCase(value: string) {
  return value
    .replaceAll("_", " ")
    .split(" ")
    .filter(Boolean)
    .map((part) => `${part[0]?.toUpperCase() ?? ""}${part.slice(1)}`)
    .join(" ");
}
