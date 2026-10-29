import test from "node:test";
import assert from "node:assert/strict";
import { resolveApiOrigin } from "../config/api-origin.mjs";

test("origem local usa somente loopback e normaliza a barra", () => {
  assert.equal(resolveApiOrigin(undefined), "http://127.0.0.1:8000");
  assert.equal(resolveApiOrigin("http://localhost:8000/"), "http://localhost:8000");
});

test("ambientes remotos exigem origem HTTPS explícita", () => {
  for (const environment of ["preview", "staging", "production"]) {
    assert.throws(() => resolveApiOrigin(undefined, environment));
    assert.throws(() => resolveApiOrigin("http://localhost:8000", environment));
    assert.equal(resolveApiOrigin("https://api.example.invalid/", environment), "https://api.example.invalid");
  }
});

test("configuração equivocada não redireciona credenciais ou caminhos", () => {
  for (const origin of ["https://user:secret@example.invalid", "https://example.invalid/api", "https://example.invalid?token=x", "https://example.invalid/#x", "http://example.invalid", "file:///tmp/api"]) {
    assert.throws(() => resolveApiOrigin(origin));
  }
  assert.throws(() => resolveApiOrigin(undefined, "producao"));
});
