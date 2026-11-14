const $ = (id) => document.getElementById(id);

async function refreshFee() {
  const amount = $("amount").value;
  const kind = $("kind").value;
  const r = await fetch(`/api/fee?amount=${encodeURIComponent(amount)}&kind=${kind}`);
  const body = await r.json();
  $("fee").textContent = r.ok ? body.fee_display : "–";
}

async function send() {
  const r = await fetch("/api/transfer", {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-User": "u-anna" },
    body: JSON.stringify({
      account_id: "acc-anna", to_iban: $("to").value, amount: $("amount").value,
      kind: $("kind").value, idempotency_key: crypto.randomUUID(),
    }),
  });
  const body = await r.json();
  $("result").textContent = r.ok ? `Transfer #${body.transfer_id} is pending.` : `Error: ${body.error}`;
}

// REQ-UI-602: remember the last used transfer type.
const KIND_KEY = "kassa.lastKind";
const saved = localStorage.getItem(KIND_KEY);
if (saved) $("kind").value = saved;

$("amount").addEventListener("input", refreshFee);
$("kind").addEventListener("change", (e) => localStorage.setItem(KIND_KEY, e.target.value));
$("send").addEventListener("click", send);
refreshFee();
