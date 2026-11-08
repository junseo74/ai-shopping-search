import { collect,finish,text,safeUrl } from './common.mjs';
export function normalize(data) {
  if(!data?.product) {if(data?.status===0)return finish([]);throw new Error('schema');}
  const p=data.product;
  return finish([{source:'openfoodfacts',name:text(p.product_name),price:null,currency:null,
    seller:text(p.stores),product_id:text(p.code),product_url:safeUrl(p.url,['openfoodfacts.org']),
    image_url:safeUrl(p.image_url,['openfoodfacts.org']),price_kind:'not_provided',
    attribution:'Open Food Facts — ODbL database / DbCL contents; images CC BY-SA and third-party rights',
  }]);
}
export const run=options=>collect('off',normalize,options);
