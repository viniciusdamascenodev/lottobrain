/** Origem do proxy no servidor; nunca exportada como configuração pública. */
export function resolveApiOrigin(value, environment = "local") {
  const environments = ["local", "test", "preview", "staging", "production"];
  if (!environments.includes(environment)) throw new Error("LOTTOBRAIN_ENV inválido.");
  const local = ["local", "test"].includes(environment);
  const origin = value || (local ? "http://127.0.0.1:8000" : "");
  let url;
  try { url = new URL(origin); } catch { throw new Error("Defina LOTTOBRAIN_API_ORIGIN válida."); }
  const loopback = ["localhost", "127.0.0.1", "[::1]"].includes(url.hostname);
  if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password ||
      url.pathname !== '/' || url.search || url.hash ||
      (url.protocol === 'http:' && (!local || !loopback))) {
    throw new Error("Origem da API deve usar HTTPS; HTTP somente em loopback local, sem credenciais ou caminho.");
  }
  return url.origin;
}
