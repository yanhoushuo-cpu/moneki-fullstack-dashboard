import { ArrowUpRight } from 'lucide-react';

import type { TopProduct } from '../../api/types';
import { formatMoney, formatNumber } from '../../lib/format';

interface TopProductsProps {
  products: TopProduct[];
  highlightedProduct: string | null;
}

export function TopProducts({ products, highlightedProduct }: TopProductsProps) {
  return (
    <section className="panel table-panel" aria-labelledby="top-products-title">
      <header className="panel-heading compact">
        <div>
          <p className="section-kicker">MENU MOMENTUM</p>
          <h2 id="top-products-title">Top 商品</h2>
          <p>按营业额排序，识别最有价值的菜单贡献。</p>
        </div>
        <span className="rank-badge"><ArrowUpRight size={15} /> TOP 10</span>
      </header>
      <div className="table-scroll">
        <table>
          <thead>
            <tr><th>排名</th><th>商品</th><th>销量</th><th>订单</th><th>营业额</th></tr>
          </thead>
          <tbody>
            {products.map((product, index) => (
              <tr key={product.product_id} className={product.product_name === highlightedProduct ? 'is-highlighted' : ''}>
                <td><span className={`rank rank-${index + 1}`}>{String(index + 1).padStart(2, '0')}</span></td>
                <td><strong>{product.product_name}</strong><small>{product.product_category}</small></td>
                <td>{formatNumber(product.quantity)}</td>
                <td>{formatNumber(product.order_count)}</td>
                <td><strong>{formatMoney(product.revenue)}</strong></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {!products.length && <div className="empty-state">所选范围没有商品销售记录。</div>}
    </section>
  );
}

