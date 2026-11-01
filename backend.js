'use strict';
let serverSession = null;
const csrfToken = () => document.cookie.split('; ').find(x => x.startsWith('csrftoken='))?.split('=')[1] || '';
async function submitServerCart(items, initial) {
  if (!serverSession.authenticated) {
    location.href = '/accounts/login/?next=' + encodeURIComponent('/');
    return;
  }
  const response = await fetch('/api/cart/import/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': csrfToken()
    },
    body: JSON.stringify({
      items,
      ...initial
    })
  });
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || 'تعذر حفظ السلة.');
  location.href = result.checkout_url;
}
async function connectStore() {
  if (!location.protocol.startsWith('http')) return;
  try {
    const response = await fetch('/api/session/');
    if (!response.ok) return;
    serverSession = await response.json();
    const catalogResponse = await fetch('/api/catalog/');
    if (!catalogResponse.ok) throw Error('تعذر تحميل المنتجات.');
    const catalog = (await catalogResponse.json()).products;
    const link = document.createElement('a');
    link.href = '/orders/';
    link.textContent = serverSession.authenticated ? 'طلباتي وحسابي' : 'تسجيل الدخول والطلبات';
    link.style.cssText = 'display:block;text-align:center;padding:12px;background:#fff;color:#23483f';
    document.body.prepend(link);

    for (const element of productElements) element.hidden = true;
    for (const p of catalog) {
      let item = products.find(x => String(x.id) === p.code);
      let element = productElements.find(x => x.dataset.id === p.code);
      if (!element) {
        element = document.createElement('article');
        element.className = 'product-card';
        const info = document.createElement('div');
        info.className = 'product-info';
        const category = document.createElement('span');
        category.className = 'product-category';
        const title = document.createElement('h3'),
          desc = document.createElement('p'),
          price = document.createElement('div');
        price.className = 'price';
        const add = document.createElement('button');
        add.type = 'button';
        add.className = 'add-cart';
        add.textContent = 'إضافة إلى السلة';
        add.addEventListener('click', () => addToCart(Number(p.code)));
        info.append(category, title, desc, price, add);
        element.append(info);
        document.getElementById('productGrid').append(element);
        productElements.push(element);
      }
      element.hidden = false;
      element.dataset.name = p.name;
      element.dataset.category = p.category;
      element.dataset.price = p.price;
      element.dataset.id = p.code;
      element.querySelector('h3').textContent = p.name;
      element.querySelector('.price').textContent = p.price + ' ر.س';
      element.querySelector('.product-category').textContent = p.category;
      const button = element.querySelector('.add-cart');
      button.disabled = p.stock === 0;
      const record = {
        id: Number(p.code),
        name: p.name,
        category: p.category,
        price: Number(p.price)
      };
      if (item) Object.assign(item, record);
      else products.push(record);
    }
    const currentCodes = new Set(catalog.map(p=>p.code));
    cart=cart.filter(item=>currentCodes.has(String(item.id)));
    saveCart();
    const form = document.getElementById('orderForm');
    document.getElementById('orderSubmit').textContent = 'حفظ الطلب والمتابعة';
    document.getElementById('orderSubmit').disabled = cart.length === 0;
    document.getElementById('orderStatus').textContent = 'تُحسب الأسعار والكميات من المتجر عند تأكيد الطلب.';
    form.addEventListener('submit', async event => {
      event.preventDefault();
      event.stopImmediatePropagation();
      const button = document.getElementById('orderSubmit');
      button.disabled = true;
      const values = new FormData(form);
      try {
        await submitServerCart(cart.map(x => ({
          code: String(x.id),
          quantity: x.quantity
        })), {
          full_name: values.get('customer'),
          phone: values.get('phone'),
          city: values.get('city'),
          address: 'السيارة: ' + values.get('vehicle')
        });
      } catch (error) {
        document.getElementById('orderStatus').textContent = error.message;
        button.disabled = false;
      }
    }, true);
    updateOrderAvailability = count => {
      document.getElementById('orderSubmit').disabled = count === 0;
      document.getElementById('orderStatus').textContent = count ? 'تُحفظ الكميات والأسعار من المتجر عند تأكيد الطلب.' : 'أضف منتجات لإتمام الطلب.';
    };
    renderCart();

  } catch (error) {
    console.warn('تعذر الاتصال بالمتجر', error.message);
  }
}
connectStore();
