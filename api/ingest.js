"use strict";
const https = require("https");

// ── HTTPS helpers ──────────────────────────────────────────────────
function httpsRequest(opts, body) {
  return new Promise((resolve, reject) => {
    const req = https.request(opts, (res) => {
      let data = "";
      res.on("data", (c) => (data += c));
      res.on("end", () => {
        let parsed;
        try { parsed = JSON.parse(data); } catch { parsed = data; }
        resolve({ status: res.statusCode, body: parsed });
      });
    });
    req.on("error", reject);
    if (body !== undefined && body !== null) req.write(JSON.stringify(body));
    req.end();
  });
}

function httpsGet(hostname, path, headers) {
  return httpsRequest({ hostname, path, method: "GET", headers: headers || {} }, null);
}

// ── Similarity helpers ─────────────────────────────────────────────
function nameSimilarity(a, b) {
  a = (a || "").toLowerCase().trim();
  b = (b || "").toLowerCase().trim();
  if (!a || !b) return 0;
  if (a === b) return 1;
  if (a.includes(b) || b.includes(a)) return 0.9;
  const wordsA = new Set(a.split(/\W+/).filter((w) => w.length >= 3));
  const wordsB = new Set(b.split(/\W+/).filter((w) => w.length >= 3));
  const common = [...wordsA].filter((w) => wordsB.has(w)).length;
  const total = Math.max(wordsA.size, wordsB.size);
  return total > 0 ? common / total : 0;
}

function jaccard(a, b) {
  const setA = new Set(a || []);
  const setB = new Set(b || []);
  if (!setA.size && !setB.size) return 0;
  const inter = [...setA].filter((x) => setB.has(x)).length;
  const union = new Set([...(a || []), ...(b || [])]).size;
  return union > 0 ? inter / union : 0;
}

function slugify(name) {
  return (name || "").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
}

// ── Handler ────────────────────────────────────────────────────────
module.exports = async function handler(req, res) {
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "POST, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type");

  if (req.method === "OPTIONS") return res.status(200).end();
  if (req.method !== "POST") return res.status(405).json({ error: "Method not allowed" });

  const { content, source = "manual", image_base64 } = req.body || {};
  if (!content && !image_base64) {
    return res.status(400).json({ error: "content is required" });
  }

  const OPENAI_KEY    = process.env.OPENAI_API_KEY;
  const GITHUB_TOKEN  = process.env.GITHUB_TOKEN;
  const OWNER         = process.env.GITHUB_OWNER || "douglaspmcgowan";
  const REPO          = process.env.GITHUB_REPO  || "ai-engineering-design-db";
  const MODEL         = process.env.OPENAI_MODEL || "gpt-5.4";

  if (!OPENAI_KEY)   return res.status(500).json({ error: "OPENAI_API_KEY not configured" });
  if (!GITHUB_TOKEN) return res.status(500).json({ error: "GITHUB_TOKEN not configured" });

  try {
    // ── 1. Extract record with GPT-5.4 ────────────────────────────
    const systemPrompt =
      "You are an expert at cataloging AI/ML tools for engineering design. " +
      "Extract a structured JSON record from the provided content. " +
      "Return ONLY valid JSON with no markdown fences or explanation. " +
      "Fields: name (string), organization (string), " +
      "category (one of: program-cad, text-to-cad, topology-optimization, neural-operator, " +
      "generative-3d-shape, generative-materials, dfm-dfam, cad-copilot, simulation-surrogate, " +
      "pinn, b-rep-learning, benchmark-dataset, metamaterial, scientific-ml, inverse-design, " +
      "eda-chip, pcb-electronics, aec-construction, robotics-manufacturing, vision-inspection, " +
      "additive-mfg, dfm-machining, medical-device, engineering-rag, scan-to-cad, " +
      "differentiable-physics, other), " +
      "year (4-digit integer), description (80-200 words), url (string or empty), " +
      "url_paper (string or empty), techniques (array of 2-8 lowercase kebab-case strings), " +
      "input_modality (string), output_modality (string), physics_domain (string or empty), " +
      "industry_application (array), tags (empty array).";

    const userContent = [
      { type: "text", text: "Extract a database record from this content:\n\n" + (content || "") },
    ];
    if (image_base64) {
      userContent.push({
        type: "image_url",
        image_url: { url: "data:image/jpeg;base64," + image_base64 },
      });
    }

    const aiResp = await httpsRequest(
      {
        hostname: "api.openai.com",
        path: "/v1/chat/completions",
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: "Bearer " + OPENAI_KEY,
        },
      },
      {
        model: MODEL,
        max_tokens: 1500,
        messages: [
          { role: "system", content: systemPrompt },
          { role: "user",   content: userContent  },
        ],
      }
    );

    if (aiResp.status !== 200) {
      const msg = (aiResp.body && aiResp.body.error && aiResp.body.error.message) || ("HTTP " + aiResp.status);
      return res.status(502).json({ error: "OpenAI error: " + msg });
    }

    let extracted;
    try {
      const raw = aiResp.body.choices[0].message.content.trim();
      const cleaned = raw.replace(/^```(?:json)?\s*/i, "").replace(/```\s*$/i, "").trim();
      extracted = JSON.parse(cleaned);
    } catch {
      return res.status(502).json({ error: "Could not parse GPT response as JSON" });
    }
    extracted.id = slugify(extracted.name || "unknown");

    // ── 2. Load consolidated.jsonl for duplicate + novelty ─────────
    let existingRecords = [];
    try {
      const dbResp = await httpsGet(
        "raw.githubusercontent.com",
        "/" + OWNER + "/" + REPO + "/main/consolidated.jsonl",
        { "User-Agent": "ai-eng-db-ingest/1.0" }
      );
      if (typeof dbResp.body === "string") {
        existingRecords = dbResp.body
          .split("\n")
          .filter(Boolean)
          .map((line) => { try { return JSON.parse(line); } catch { return null; } })
          .filter(Boolean);
      }
    } catch { /* proceed without existing data */ }

    // ── 3. Duplicate check ─────────────────────────────────────────
    for (const rec of existingRecords) {
      if (nameSimilarity(extracted.name, rec.name) >= 0.75) {
        return res.status(200).json({
          status: "duplicate",
          name: extracted.name,
          matchedName: rec.name,
          matchedRecord: {
            name: rec.name,
            organization: rec.organization,
            year: rec.year,
            category: rec.category,
            url: rec.url || rec.url_paper || "",
          },
          message: '"' + extracted.name + '" already exists as "' + rec.name + '"',
        });
      }
    }

    // ── 4. Novelty score via Jaccard on techniques ─────────────────
    const scored = existingRecords
      .map((rec) => ({
        name: rec.name,
        org: rec.organization || "",
        category: rec.category || "",
        score: jaccard(extracted.techniques, rec.techniques),
      }))
      .filter((r) => r.score > 0)
      .sort((a, b) => b.score - a.score)
      .slice(0, 5);

    const avgSim = scored.length > 0
      ? scored.reduce((s, r) => s + r.score, 0) / scored.length
      : 0;
    const noveltyScore = Math.round((1 - avgSim) * 100) / 10;
    const similar = scored.slice(0, 3).map((r) => ({
      name: r.name,
      org: r.org,
      category: r.category,
      similarity_pct: Math.round(r.score * 100),
    }));

    // ── 5. Commit to raw/inbox.jsonl via GitHub API ────────────────
    const ghHeaders = {
      Authorization: "Bearer " + GITHUB_TOKEN,
      "User-Agent": "ai-eng-db-ingest/1.0",
      Accept: "application/vnd.github+json",
      "Content-Type": "application/json",
    };

    const fileResp = await httpsGet(
      "api.github.com",
      "/repos/" + OWNER + "/" + REPO + "/contents/raw/inbox.jsonl",
      ghHeaders
    );

    let existingContent = "";
    let sha;
    if (fileResp.status === 200 && fileResp.body && fileResp.body.content) {
      existingContent = Buffer.from(
        fileResp.body.content.replace(/\n/g, ""), "base64"
      ).toString("utf8");
      sha = fileResp.body.sha;
    }

    const newRecord = Object.assign({}, extracted, {
      source,
      ingested_at: new Date().toISOString(),
    });
    const updatedContent = existingContent + JSON.stringify(newRecord) + "\n";

    const putBody = {
      message: "ingest: add " + extracted.name,
      content: Buffer.from(updatedContent).toString("base64"),
    };
    if (sha) putBody.sha = sha;

    const putResp = await httpsRequest(
      {
        hostname: "api.github.com",
        path: "/repos/" + OWNER + "/" + REPO + "/contents/raw/inbox.jsonl",
        method: "PUT",
        headers: ghHeaders,
      },
      putBody
    );

    if (putResp.status !== 200 && putResp.status !== 201) {
      return res.status(502).json({
        error: "GitHub commit failed (" + putResp.status + "): " +
          ((putResp.body && putResp.body.message) || "unknown"),
      });
    }

    // ── 6. Success ─────────────────────────────────────────────────
    return res.status(200).json({
      status: "added",
      name: extracted.name,
      org: extracted.organization,
      year: extracted.year,
      category: extracted.category,
      description: extracted.description,
      techniques: extracted.techniques || [],
      similar,
      novelty_score: noveltyScore,
      message: "Added to inbox. Next graph rebuild runs automatically every 2 days.",
    });

  } catch (err) {
    console.error("[ingest]", err);
    return res.status(500).json({ error: err.message || "Internal server error" });
  }
};
