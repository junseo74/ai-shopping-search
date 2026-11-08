// No credentials, cookies, redirects, retries, or arbitrary endpoint access.
export const endpoints = Object.freeze({
  apple: 'https://itunes.apple.com/search?term=notion&country=us&entity=software&limit=3',
  off: 'https://world.openfoodfacts.org/api/v3/product/3017620422003?fields=code,product_name,brands,stores,image_url,url',
  prices: 'https://prices.openfoodfacts.org/api/v1/prices?product_code=3017620422003&size=3',
});
export async function request(id, { fetcher = fetch, timeoutMs = 15000, maxBytes = 1000000 } = {}) {
  if (!Object.hasOwn(endpoints, id)) throw new Error('endpoint_not_allowed');
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  let reader;
  try {
    const res = await fetcher(endpoints[id], { method: 'GET', redirect: 'manual', credentials: 'omit',
      signal: controller.signal, headers: { 'User-Agent': 'AIShoppingSourceResearch/3.0 (three-record public API validation)', Accept: 'application/json' } });
    if (res.status !== 200) return { status: 'http_error', http_status: res.status };
    reader = res.body.getReader();
    const chunks = []; let length = 0;
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      length += value.length;
      if (length > maxBytes) { await reader.cancel(); return { status: 'size_limit', http_status: 200 }; }
      chunks.push(value);
    }
    let data;
    try { data = JSON.parse(Buffer.concat(chunks).toString('utf8')); }
    catch { return { status: 'invalid_json', http_status: 200 }; }
    return { status: 'ok', http_status: 200, bytes: length, data };
  } catch {
    return { status: controller.signal.aborted ? 'timeout' : 'network_error', http_status: null };
  } finally { clearTimeout(timer); reader?.releaseLock(); }
}
