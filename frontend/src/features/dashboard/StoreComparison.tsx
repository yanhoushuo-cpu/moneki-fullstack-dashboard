import { MapPin } from 'lucide-react';

import type { StoreComparison as StoreComparisonType } from '../../api/types';
import { formatMoney, formatNumber } from '../../lib/format';

export function StoreComparison({ stores }: { stores: StoreComparisonType[] }) {
  return (
    <section className="panel stores-panel" aria-labelledby="stores-title">
      <header className="panel-heading compact">
        <div>
          <p className="section-kicker">STORE MIX</p>
          <h2 id="stores-title">门店贡献</h2>
          <p>同一区间内的门店营业额占比。</p>
        </div>
      </header>
      <div className="store-list">
        {stores.map((store, index) => (
          <article className="store-row" key={store.store_id}>
            <span className="store-index">{String(index + 1).padStart(2, '0')}</span>
            <div className="store-copy">
              <div><strong>{store.store_name}</strong><span>{store.category}</span></div>
              <small><MapPin size={13} />{store.district} · {formatNumber(store.order_count)} 单</small>
              <div className="progress-track"><span style={{ width: `${store.share_percent}%` }} /></div>
            </div>
            <div className="store-value"><strong>{formatMoney(store.revenue)}</strong><span>{store.share_percent.toFixed(1)}%</span></div>
          </article>
        ))}
      </div>
      {!stores.length && <div className="empty-state">所选范围没有门店数据。</div>}
    </section>
  );
}

