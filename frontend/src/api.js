// Calls to the statistics API. In dev, Vite proxies /api/... to http://127.0.0.1:8000/...

export async function api(path, token) {
  const res = await fetch(`/api${path}`, { headers: { Authorization: `Bearer ${token}` } })
  const text = await res.text()
  let body
  try {
    body = JSON.parse(text)
  } catch {
    body = { detail: [{ msg: text }] }
  }
  if (!res.ok) {
    // the API always answers errors with {"detail": [{"msg": ...}, ...]}
    const msgs = Array.isArray(body.detail) ? body.detail.map((d) => d.msg) : [String(body.detail)]
    throw new Error(`${res.status}: ${msgs.join('; ')}`)
  }
  return body
}

export function simPath(user, simulation) {
  return `/users/${encodeURIComponent(user)}/simulations/${encodeURIComponent(simulation)}`
}

export function statsPath(user, simulation, { attribute, stat, outputs, parts }) {
  const q = new URLSearchParams({ attribute, stat, outputs: outputs.join(','), parts: parts.join(',') }).toString()
  return `${simPath(user, simulation)}/stats?${q}`
}
