import { logger } from "https://deno.land/x/hono@v3.11.4/middleware.ts";
import { Hono } from "https://deno.land/x/hono@v3.11.4/mod.ts";

const configPath = Deno.args[0] || "./config.json";
console.log(`Loading config from ${configPath}`);
const config = JSON.parse(await Deno.readTextFile(configPath));

const app = new Hono();

app.use("*", logger());

app.post("/:slug", async (c) => {
  const slug = c.req.param("slug");

  const resp = await fetch(`${config.proxy}/${slug}`, {
    method: "POST",
    body: c.req.raw.body,
  });

  c.status(resp.status);
  if (resp.ok) {
    return c.json(await resp.json());
  } else {
    return c.text(await resp.text());
  }
});

Deno.serve({ port: 3000, hostname: "0.0.0.0" }, app.fetch);
