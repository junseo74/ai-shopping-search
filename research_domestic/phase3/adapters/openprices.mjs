import { collect,finish,text,amount,safeUrl } from './common.mjs';
export function normalize(data) {
  if(!Array.isArray(data?.items))throw new Error('schema');
  return finish(data.items.slice(0,3).map(p=>({source:'openprices',
    name:text(p.product?.product_name)||text(p.product_name),price:amount(p.price),
    currency:/^[A-Z]{3}$/.test(p.currency)?p.currency:null,
    seller:text(p.location?.osm_name)||text(p.location?.osm_brand),
    // A dated observation is a separate offer; barcode alone would wrongly deduplicate history.
    product_id:p.id===null||p.id===undefined?null:String(p.id),barcode:text(p.product_code),
    product_url:null, // No merchant product page field in the verified response.
    image_url:safeUrl(p.product?.image_url,['openfoodfacts.org']),
    price_kind:'historical_crowdsourced_observation_not_current_retail_offer',
    price_observed_date:/^\d{4}-\d{2}-\d{2}$/.test(p.date)?p.date:null,
    attribution:'Open Prices / Open Food Facts — ODbL; no receipt/owner/location details retained',
  })));
}
export const run=options=>collect('prices',normalize,options);
