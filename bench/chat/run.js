// node bench/chat/run.js <version|floor> <split:dev|heldout|all> [k]
// Runs the real app/api/ask.js handler on every case and stores traces in runs/<version>.<split>.json.
const fs = require("fs");
const path = require("path");
const [version, split = "dev", kArg = "1"] = process.argv.slice(2);
const k = Number(kArg);
process.env.PROMPT_VERSION = version === "floor" ? "v1" : version;
if (version === "floor") delete process.env.GEMINI_API_KEY;
const handler = require("../../app/api/ask.js");
const cases = JSON.parse(fs.readFileSync(path.join(__dirname, "cases.json"))).filter((c) => split === "all" || c.split === split);

function call(c) {
  return new Promise((resolve) => {
    const t0 = Date.now();
    const req = { method: "POST", body: { pr: c.pr, question: c.question, history: [] } };
    const res = {
      statusCode: 200, setHeader() {},
      end(s) { const j = JSON.parse(s); resolve({ id: c.id, answer: j.answer, source: j.source, ms: Date.now() - t0 }); },
    };
    handler(req, res);
  });
}

(async () => {
  const jobs = [];
  for (const c of cases) for (let r = 0; r < k; r++) jobs.push({ c, r });
  const out = [];
  let i = 0;
  async function worker() {
    while (i < jobs.length) {
      const { c, r } = jobs[i++];
      let t = await call(c);
      if (version !== "floor" && t.source === "trailer") t = await call(c); // one retry on API error
      out.push({ ...t, rep: r });
    }
  }
  await Promise.all(Array.from({ length: 6 }, worker));
  out.sort((a, b) => a.id.localeCompare(b.id) || a.rep - b.rep);
  fs.mkdirSync(path.join(__dirname, "runs"), { recursive: true });
  fs.writeFileSync(path.join(__dirname, "runs", `${version}.${split}.k${k}.json`), JSON.stringify(out, null, 1));
  const fell = out.filter((t) => t.source === "trailer").length;
  console.log(`${version} ${split} k=${k}: ${out.length} traces, ${fell} from rules, median ${out.map((t) => t.ms).sort((a, b) => a - b)[out.length >> 1]} ms`);
})();
