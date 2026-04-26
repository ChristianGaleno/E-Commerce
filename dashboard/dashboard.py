import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st
import warnings
warnings.filterwarnings('ignore')

st.title('Dashboard Analisis E-Commerce Olist')
st.write('Proyek Analisis Data | Christian Galeno')

# Load data
orders = pd.read_csv('orders_dataset.csv')
order_items = pd.read_csv('order_items_dataset.csv')
order_payments = pd.read_csv('order_payments_dataset.csv')
order_reviews = pd.read_csv('order_reviews_dataset.csv')
products = pd.read_csv('products_dataset.csv')
category_translation = pd.read_csv('product_category_name_translation.csv')

# Cleaning
date_cols = [
    'order_purchase_timestamp', 'order_approved_at',
    'order_delivered_carrier_date', 'order_delivered_customer_date',
    'order_estimated_delivery_date'
]
for col in date_cols:
    orders[col] = pd.to_datetime(orders[col])

orders_clean = orders[orders['order_status'] == 'delivered'].copy()
orders_clean = orders_clean.dropna(subset=['order_delivered_customer_date'])
orders_clean['order_date'] = orders_clean['order_purchase_timestamp'].dt.date
orders_clean['year_month'] = orders_clean['order_purchase_timestamp'].dt.to_period('M')

products['product_category_name'] = products['product_category_name'].fillna('unknown')
products = products.merge(category_translation, on='product_category_name', how='left')
products['category_en'] = products['product_category_name_english'].fillna(products['product_category_name'])

payment_per_order = order_payments.groupby('order_id')['payment_value'].sum().reset_index()
revenue_df = orders_clean.merge(payment_per_order, on='order_id', how='left')

# =====================
# SIDEBAR - FILTER TANGGAL (FITUR INTERAKTIF)
# =====================
st.sidebar.header('Filter Data')

min_date = orders_clean['order_purchase_timestamp'].min().date()
max_date = orders_clean['order_purchase_timestamp'].max().date()

start_date = st.sidebar.date_input('Tanggal Mulai', value=min_date, min_value=min_date, max_value=max_date)
end_date = st.sidebar.date_input('Tanggal Akhir', value=max_date, min_value=min_date, max_value=max_date)

if start_date > end_date:
    st.sidebar.error('Tanggal mulai tidak boleh lebih besar dari tanggal akhir.')

filtered = revenue_df[
    (revenue_df['order_date'] >= start_date) &
    (revenue_df['order_date'] <= end_date)
]

st.sidebar.markdown('---')
pertanyaan = st.sidebar.radio(
    'Pilih Analisis:',
    ['Tren Pendapatan Bulanan', 'Revenue & Review Score per Kategori']
)

st.caption(f"Menampilkan data: **{start_date}** s/d **{end_date}** | Total order: **{len(filtered):,}**")

# =====================
# PERTANYAAN 1
# =====================
if pertanyaan == 'Tren Pendapatan Bulanan':
    st.header('Tren Pendapatan Bulanan Olist')

    monthly_rev = filtered.groupby('year_month')['payment_value'].sum().reset_index()
    monthly_rev.columns = ['year_month', 'revenue']
    monthly_rev = monthly_rev.sort_values('year_month')
    monthly_rev['mom_growth'] = monthly_rev['revenue'].pct_change() * 100

    col1, col2, col3 = st.columns(3)
    col1.metric('Total Revenue', f"R$ {monthly_rev['revenue'].sum():,.0f}")
    col2.metric('Bulan Terbaik', str(monthly_rev.loc[monthly_rev['revenue'].idxmax(), 'year_month']))
    col3.metric('Rata-rata/Bulan', f"R$ {monthly_rev['revenue'].mean():,.0f}")

    st.subheader('Grafik Tren Revenue')
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(monthly_rev['year_month'].astype(str), monthly_rev['revenue'], marker='o')
    ax.set_xlabel('Bulan')
    ax.set_ylabel('Revenue (BRL)')
    ax.set_title('Tren Pendapatan Bulanan')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    st.pyplot(fig)

    st.subheader('Month-over-Month Growth (%)')
    fig2, ax2 = plt.subplots(figsize=(10, 3))
    ax2.bar(monthly_rev['year_month'].astype(str), monthly_rev['mom_growth'])
    ax2.axhline(0, color='black', linewidth=0.8)
    ax2.set_xlabel('Bulan')
    ax2.set_ylabel('MoM Growth (%)')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    st.pyplot(fig2)

    st.subheader('Data Lengkap')
    st.dataframe(monthly_rev.rename(columns={
        'year_month': 'Bulan',
        'revenue': 'Revenue (BRL)',
        'mom_growth': 'MoM Growth (%)'
    }))

# =====================
# PERTANYAAN 2
# =====================
else:
    st.header('Revenue & Review Score per Kategori (Top 20)')

    orders_filtered = orders_clean[
        (orders_clean['order_date'] >= start_date) &
        (orders_clean['order_date'] <= end_date)
    ]

    items_cat = orders_filtered.merge(
        order_items[['order_id', 'product_id', 'price']], on='order_id', how='left'
    ).merge(products[['product_id', 'category_en']], on='product_id', how='left')

    cat_rev = items_cat.groupby('category_en')['price'].sum().reset_index()
    cat_rev.columns = ['category_en', 'total_revenue']

    cat_review = (
        orders_filtered
        .merge(order_reviews[['order_id', 'review_score']], on='order_id', how='left')
        .merge(order_items[['order_id', 'product_id']], on='order_id', how='left')
        .merge(products[['product_id', 'category_en']], on='product_id', how='left')
    )
    cat_score = cat_review.groupby('category_en')['review_score'].mean().reset_index()
    cat_score.columns = ['category_en', 'avg_score']

    cat_summary = cat_rev.merge(cat_score, on='category_en').dropna()
    top20 = cat_summary.sort_values('total_revenue', ascending=False).head(20).reset_index(drop=True)
    platform_avg = order_reviews['review_score'].mean()

    col1, col2 = st.columns(2)
    col1.metric('Rata-rata Review Platform', f"{platform_avg:.2f}")
    col2.metric('Kategori Score < 4.0', len(top20[top20['avg_score'] < 4.0]))

    st.subheader('Total Revenue per Kategori')
    fig, ax = plt.subplots(figsize=(8, 7))
    ax.barh(top20['category_en'], top20['total_revenue'])
    ax.set_xlabel('Total Revenue (BRL)')
    ax.set_title('Top 20 Kategori - Total Revenue')
    plt.tight_layout()
    st.pyplot(fig)

    st.subheader('Rata-rata Review Score per Kategori')
    fig2, ax2 = plt.subplots(figsize=(8, 7))
    ax2.barh(top20['category_en'], top20['avg_score'])
    ax2.axvline(4.0, color='red', linestyle='--', label='Threshold 4.0')
    ax2.axvline(platform_avg, color='orange', linestyle='--', label=f'Rata-rata platform ({platform_avg:.2f})')
    ax2.set_xlabel('Avg Review Score')
    ax2.set_title('Review Score per Kategori')
    ax2.legend()
    plt.tight_layout()
    st.pyplot(fig2)

    st.subheader('Kategori dengan Score < 4.0')
    needs_attention = top20[top20['avg_score'] < 4.0][['category_en', 'total_revenue', 'avg_score']]
    st.dataframe(needs_attention.rename(columns={
        'category_en': 'Kategori',
        'total_revenue': 'Total Revenue (BRL)',
        'avg_score': 'Avg Review Score'
    }))
