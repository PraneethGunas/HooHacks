import type { LightningPaymentEvent } from "@/types/pipeline";
import { cn } from "@/lib/utils";

interface Props {
  payment: LightningPaymentEvent["data"];
}

function BoltIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true">
      <path d="M9.5 1L3 9h5.5L6.5 15 13 7H7.5L9.5 1z" fill="#F59E0B" />
    </svg>
  );
}

export default function LightningRow({ payment }: Props) {
  return (
    <div className="lightning-flash my-2 flex items-center gap-3 rounded-lg border border-amber-500/30 bg-amber-950/30 px-3 py-2.5 enter-card">
      <BoltIcon />
      <div className="flex-1 text-xs text-amber-200/85">
        <span className="font-medium text-amber-100">Lightning payment</span>
        {" · "}
        {payment.invoice_amount_sats} sats → {payment.service}
      </div>
      {payment.duration_ms > 0 && (
        <div className="text-[10px] text-amber-100/70">{Math.round(payment.duration_ms)}ms</div>
      )}
      <span
        className={cn(
          "rounded px-2 py-0.5 text-[10px] font-medium",
          payment.status === "paid" && "bg-amber-500 text-amber-950",
          payment.status === "paying" && "bg-amber-900 text-amber-300 animate-pulse",
          payment.status === "failed" && "bg-red-900 text-red-300",
        )}
      >
        {payment.status}
      </span>
    </div>
  );
}
