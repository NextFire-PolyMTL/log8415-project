import { logger } from "https://deno.land/x/hono@v3.11.4/middleware.ts";
import { Hono } from "https://deno.land/x/hono@v3.11.4/mod.ts";

// Load config file
const configPath = Deno.args[0] || "./config.json";
console.log(`Loading config from ${configPath}`);
const config = JSON.parse(await Deno.readTextFile(configPath));

const app = new Hono();

app.use("*", logger());

app.post("/:slug", async (c) => {
  const slug = c.req.param("slug");

  // Forward request to trusted host
  const resp = await fetch(`${config.trusted}/${slug}`, {
    method: "POST",
    body: c.req.raw.body,
  });

  // Return response from trusted host
  c.status(resp.status);
  let json;
  try {
    json = await resp.json();
  } catch {
    json = [];
  }
  return c.json(json);
});

Deno.serve({ port: 3000, hostname: "0.0.0.0" }, app.fetch);
