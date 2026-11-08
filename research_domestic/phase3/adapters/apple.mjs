// Live-confirmed software response. This adapter does not implement untested song schemas.
import { collect,finish,text,amount,safeUrl } from './common.mjs';
export function normalize(data) {
  if(!Array.isArray(data?.results)) throw new Error('schema');
  return finish(data.results.slice(0,3).map(p=>({source:'apple',
    name:text(p.trackName),price:amount(p.price),currency:/^[A-Z]{3}$/.test(p.currency)?p.currency:null,
    seller:text(p.sellerName),product_id:p.trackId===null||p.trackId===undefined?null:String(p.trackId),
    product_url:safeUrl(p.trackViewUrl,['apps.apple.com','itunes.apple.com']),
    image_url:safeUrl(p.artworkUrl512||p.artworkUrl100,['mzstatic.com']),
    price_kind:'app_store_base_price_excludes_in_app_purchases',
    attribution:'Apple App Store Search API; display promotion/badge/link conditions apply',
  })));
}
export const run=options=>collect('apple',normalize,options);
