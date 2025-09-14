"""Analytics page module.

Provides comprehensive financial analytics and visualizations for transaction data.
"""

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st
from typing import Dict, List, Any

from src.ui.components.navigation import show_page_header
from src.ui.styles import create_metric_card


class AnalyticsPage:
    """Analytics page with financial metrics and visualizations."""

    def __init__(self, processor):
        self.processor = processor

    def render(self):
        """Render the Analytics page."""
        show_page_header(
            "Financial Analytics",
            "Comprehensive analysis of your business expenses and vendor relationships"
        )

        try:
            # Load data
            vendor_payments = self.processor.get_vendor_payments()
            vendors = self.processor.get_all_vendors()

            if not vendor_payments or not vendors:
                st.warning("No transaction data found. Please process some CSV files first.")
                return

            # Convert to DataFrames and prepare data
            df_payments = pd.DataFrame(vendor_payments)
            df_vendors = pd.DataFrame(vendors)
            df_payments = self._prepare_payment_data(df_payments)


            # Calculate metrics
            metrics = self._calculate_financial_metrics(df_payments, df_vendors)

            # Render dashboard sections
            self._render_kpi_dashboard(metrics, df_payments)
            self._render_spending_analysis(df_payments, metrics)
            self._render_vendor_analysis(df_payments, df_vendors)
            self._render_category_analysis(df_payments)
            self._render_cash_flow_analysis(df_payments)
            self._render_business_intelligence(df_payments, df_vendors, metrics)
            self._render_detailed_tables(df_payments, df_vendors)

        except Exception as e:
            st.error(f"Error loading analytics data: {e}")
            st.code(str(e))

    def _prepare_payment_data(self, df_payments: pd.DataFrame) -> pd.DataFrame:
        """Prepare and clean payment data for analysis."""
        df_payments["date"] = pd.to_datetime(df_payments["date"])
        df_payments["amount_abs"] = df_payments["amount"].abs()
        df_payments["year_month"] = df_payments["date"].dt.to_period("M")
        return df_payments

    def _calculate_financial_metrics(self, df_payments: pd.DataFrame, df_vendors: pd.DataFrame) -> Dict[str, Any]:
        """Calculate key financial metrics."""
        current_date = df_payments["date"].max()
        monthly_spending = df_payments.groupby("year_month")["amount_abs"].sum()

        return {
            "total_spent": df_payments["amount_abs"].sum(),
            "avg_transaction": df_payments["amount_abs"].mean(),
            "unique_vendors": df_payments["vendor_name"].nunique(),
            "transaction_count": len(df_payments),
            "current_month_spending": monthly_spending.iloc[-1] if len(monthly_spending) > 0 else 0,
            "monthly_average": monthly_spending.mean() if len(monthly_spending) > 1 else 0,
            "active_vendors": len(df_vendors[df_vendors.get("transaction_count", 0) > 0]) if "transaction_count" in df_vendors.columns else 0,
            "monthly_spending": monthly_spending,
        }

    def _render_kpi_dashboard(self, metrics: Dict, df_payments: pd.DataFrame):
        """Render KPI metrics dashboard."""
        st.markdown("### Key Financial Metrics")

        col1, col2, col3, col4, col5 = st.columns(5)

        with col1:
            st.markdown(create_metric_card(
                "Total Expenses",
                f"{metrics['total_spent']:,.0f} DKK",
                f"{metrics['current_month_spending']:,.0f} this month"
            ), unsafe_allow_html=True)

        with col2:
            st.markdown(create_metric_card(
                "Active Vendors",
                f"{metrics['unique_vendors']}",
                f"{metrics['active_vendors']} with transactions"
            ), unsafe_allow_html=True)

        with col3:
            st.markdown(create_metric_card(
                "Avg Transaction",
                f"{metrics['avg_transaction']:,.0f} DKK"
            ), unsafe_allow_html=True)

        with col4:
            st.markdown(create_metric_card(
                "Total Transactions",
                f"{metrics['transaction_count']:,}"
            ), unsafe_allow_html=True)

        with col5:
            st.markdown(create_metric_card(
                "Monthly Average",
                f"{metrics['monthly_average']:,.0f} DKK"
            ), unsafe_allow_html=True)

        st.markdown("---")

    def _render_spending_analysis(self, df_payments: pd.DataFrame, metrics: Dict):
        """Render spending analysis charts."""
        st.markdown("### Spending Analysis")

        col1, col2 = st.columns([2, 1])

        with col1:
            self._render_monthly_trend_chart(metrics["monthly_spending"], metrics["monthly_average"])

        with col2:
            self._render_spending_distribution_chart(df_payments)

        st.markdown("---")

    def _render_monthly_trend_chart(self, monthly_spending: pd.Series, monthly_average: float):
        """Render monthly spending trend chart."""
        if len(monthly_spending) <= 1:
            st.info("Need more months of data to show trend analysis")
            return

        fig_trend = go.Figure()

        fig_trend.add_trace(
            go.Scatter(
                x=[str(period) for period in monthly_spending.index],
                y=monthly_spending.values,
                mode="lines+markers",
                name="Monthly Spending",
                line=dict(color="#4a9eff", width=3),
                marker=dict(size=8),
                hovertemplate="<b>%{x}</b><br>Spending: %{y:,.0f} DKK<extra></extra>"
            )
        )

        # Add average line
        fig_trend.add_hline(
            y=monthly_average,
            line_dash="dash",
            line_color="orange",
            annotation_text=f"Average: {monthly_average:,.0f} DKK",
        )

        fig_trend.update_layout(
            title="Monthly Spending Trend",
            xaxis_title="Month",
            yaxis_title="Amount (DKK)",
            height=400,
            showlegend=False,
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="white"),
            xaxis=dict(gridcolor="#333"),
            yaxis=dict(gridcolor="#333")
        )

        st.plotly_chart(fig_trend, use_container_width=True)

    def _render_spending_distribution_chart(self, df_payments: pd.DataFrame):
        """Render spending distribution chart."""
        # Create transaction size distribution
        bins = [0, 1000, 5000, 10000, 50000, float('inf')]
        labels = ['<1K', '1K-5K', '5K-10K', '10K-50K', '50K+']
        df_payments['size_category'] = pd.cut(df_payments['amount_abs'], bins=bins, labels=labels, right=False)

        distribution = df_payments['size_category'].value_counts()

        fig_dist = go.Figure(data=[
            go.Pie(
                labels=distribution.index,
                values=distribution.values,
                hole=0.4,
                marker=dict(colors=px.colors.qualitative.Set3),
                hovertemplate="<b>%{label}</b><br>Count: %{value}<br>Percentage: %{percent}<extra></extra>"
            )
        ])

        fig_dist.update_layout(
            title="Transaction Size Distribution",
            height=400,
            showlegend=True,
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="white")
        )

        st.plotly_chart(fig_dist, use_container_width=True)

    def _render_vendor_analysis(self, df_payments: pd.DataFrame, df_vendors: pd.DataFrame):
        """Render vendor analysis section."""
        st.markdown("### Vendor Analysis")

        col1, col2 = st.columns([3, 2])

        with col1:
            self._render_top_vendors_chart(df_payments)

        with col2:
            self._render_vendor_insights(df_payments, df_vendors)

        st.markdown("---")

    def _render_top_vendors_chart(self, df_payments: pd.DataFrame):
        """Render top vendors spending chart."""
        # Top 15 vendors by total spending
        top_vendors = (
            df_payments.groupby("vendor_name")["amount_abs"]
            .sum()
            .nlargest(15)
            .sort_values()
        )

        fig_vendors = go.Figure(go.Bar(
            x=top_vendors.values,
            y=top_vendors.index,
            orientation='h',
            marker=dict(color='#4a9eff'),
            hovertemplate="<b>%{y}</b><br>Total: %{x:,.0f} DKK<extra></extra>"
        ))

        fig_vendors.update_layout(
            title="Top 15 Vendors by Total Spending",
            xaxis_title="Total Spending (DKK)",
            yaxis_title="Vendor",
            height=600,
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="white"),
            xaxis=dict(gridcolor="#333"),
            yaxis=dict(gridcolor="#333")
        )

        st.plotly_chart(fig_vendors, use_container_width=True)

    def _render_vendor_insights(self, df_payments: pd.DataFrame, df_vendors: pd.DataFrame):
        """Render vendor insights and statistics."""
        st.markdown("#### Vendor Insights")

        # Calculate vendor stats
        vendor_stats = df_payments.groupby("vendor_name").agg({
            "amount_abs": ["sum", "count", "mean"],
            "date": ["min", "max"]
        }).round(2)

        vendor_stats.columns = ["total_spent", "transaction_count", "avg_transaction", "first_transaction", "last_transaction"]
        vendor_stats = vendor_stats.reset_index()

        # Top spending vendor
        top_vendor = vendor_stats.loc[vendor_stats["total_spent"].idxmax()]
        st.markdown(f"**Biggest Vendor:** {top_vendor['vendor_name']}")
        st.caption(f"Total: {top_vendor['total_spent']:,.0f} DKK across {top_vendor['transaction_count']} transactions")

        # Most frequent vendor
        most_frequent = vendor_stats.loc[vendor_stats["transaction_count"].idxmax()]
        st.markdown(f"**Most Frequent:** {most_frequent['vendor_name']}")
        st.caption(f"Count: {most_frequent['transaction_count']} transactions")

        # Highest average
        highest_avg = vendor_stats.loc[vendor_stats["avg_transaction"].idxmax()]
        st.markdown(f"**Highest Average:** {highest_avg['vendor_name']}")
        st.caption(f"Average: {highest_avg['avg_transaction']:,.0f} DKK per transaction")

        # Recent activity
        recent_vendors = df_payments[df_payments["date"] >= df_payments["date"].max() - pd.Timedelta(days=30)]
        if not recent_vendors.empty:
            recent_count = recent_vendors["vendor_name"].nunique()
            st.markdown(f"**Recent Activity:** {recent_count} vendors")
            st.caption("Active in the last 30 days")

    def _render_detailed_tables(self, df_payments: pd.DataFrame, df_vendors: pd.DataFrame):
        """Render detailed data tables."""
        st.markdown("### Detailed Data")

        tab1, tab2, tab3 = st.tabs(["Recent Transactions", "Vendor Summary", "Monthly Breakdown"])

        with tab1:
            st.markdown("#### Recent Transactions")
            recent_transactions = df_payments.nlargest(50, "date")[
                ["date", "vendor_name", "amount", "amount_abs", "category_confidence"]
            ].copy()
            recent_transactions["date"] = recent_transactions["date"].dt.strftime("%Y-%m-%d")
            recent_transactions["amount"] = recent_transactions["amount"].round(2)
            recent_transactions["amount_abs"] = recent_transactions["amount_abs"].round(2)
            recent_transactions["category_confidence"] = recent_transactions["category_confidence"].round(3)
            st.dataframe(recent_transactions, use_container_width=True)

        with tab2:
            st.markdown("#### Vendor Summary")
            vendor_summary = df_payments.groupby("vendor_name").agg({
                "amount_abs": ["sum", "count", "mean"],
                "date": ["min", "max"],
                "category_confidence": "mean"
            }).round(2)

            vendor_summary.columns = [
                "total_spending", "transaction_count", "avg_transaction",
                "first_seen", "last_seen", "avg_confidence"
            ]
            vendor_summary = vendor_summary.reset_index()
            vendor_summary["first_seen"] = pd.to_datetime(vendor_summary["first_seen"]).dt.strftime("%Y-%m-%d")
            vendor_summary["last_seen"] = pd.to_datetime(vendor_summary["last_seen"]).dt.strftime("%Y-%m-%d")
            vendor_summary = vendor_summary.sort_values("total_spending", ascending=False)
            st.dataframe(vendor_summary, use_container_width=True)

        with tab3:
            st.markdown("#### Monthly Breakdown")
            monthly_breakdown = df_payments.groupby("year_month").agg({
                "amount_abs": ["sum", "count", "mean"],
                "vendor_name": "nunique"
            }).round(2)

            monthly_breakdown.columns = ["total_spending", "transaction_count", "avg_transaction", "unique_vendors"]
            monthly_breakdown.index = monthly_breakdown.index.astype(str)
            st.dataframe(monthly_breakdown, use_container_width=True)

    def _render_category_analysis(self, df_payments: pd.DataFrame):
        """Render category analysis section."""
        st.markdown("### Category Analysis")

        # Check if category column exists
        if 'category' not in df_payments.columns:
            st.info("Category analysis requires transaction categorization. Process transactions first to enable this analysis.")
            return

        col1, col2 = st.columns([2, 1])

        with col1:
            # Category spending chart
            category_spending = df_payments.groupby('category')['amount_abs'].agg(['sum', 'count']).reset_index()
            category_spending = category_spending.sort_values('sum', ascending=True)

            fig_cat = go.Figure(go.Bar(
                x=category_spending['sum'],
                y=category_spending['category'],
                orientation='h',
                marker=dict(color='#4a9eff'),
                hovertemplate="<b>%{y}</b><br>Total: %{x:,.0f} DKK<br>Transactions: %{customdata}<extra></extra>",
                customdata=category_spending['count']
            ))

            fig_cat.update_layout(
                title="Spending by Category",
                xaxis_title="Total Spending (DKK)",
                yaxis_title="Category",
                height=400,
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="white"),
                xaxis=dict(gridcolor="#333"),
                yaxis=dict(gridcolor="#333")
            )

            st.plotly_chart(fig_cat, use_container_width=True)

        with col2:
            # Category insights
            st.markdown("#### Category Insights")

            # Top category
            top_category = category_spending.iloc[-1]
            st.markdown(f"**Highest Spending:** {top_category['category']}")
            st.caption(f"{top_category['sum']:,.0f} DKK ({top_category['count']} transactions)")

            # Average transaction per category
            avg_by_category = df_payments.groupby('category')['amount_abs'].mean().sort_values(ascending=False)
            st.markdown(f"**Highest Avg Transaction:** {avg_by_category.index[0]}")
            st.caption(f"{avg_by_category.iloc[0]:,.0f} DKK per transaction")

            # Category diversity
            unique_categories = df_payments['category'].nunique()
            st.markdown(f"**Category Diversity:** {unique_categories} categories")
            st.caption(f"Average {len(df_payments) / unique_categories:.1f} transactions per category")

        st.markdown("---")

    def _render_cash_flow_analysis(self, df_payments: pd.DataFrame):
        """Render cash flow analysis section."""
        st.markdown("### Cash Flow Analysis")

        # Prepare cash flow data
        df_payments['week'] = df_payments['date'].dt.to_period('W')
        df_payments['day_of_week'] = df_payments['date'].dt.day_name()
        df_payments['hour'] = df_payments['date'].dt.hour

        col1, col2 = st.columns(2)

        with col1:
            # Weekly cash flow
            weekly_flow = df_payments.groupby('week')['amount_abs'].sum()

            fig_weekly = go.Figure(go.Scatter(
                x=[str(w) for w in weekly_flow.index],
                y=weekly_flow.values,
                mode='lines+markers',
                name='Weekly Spending',
                line=dict(color='#4a9eff', width=2),
                marker=dict(size=6),
                hovertemplate="<b>Week %{x}</b><br>Spending: %{y:,.0f} DKK<extra></extra>"
            ))

            fig_weekly.update_layout(
                title="Weekly Spending Pattern",
                xaxis_title="Week",
                yaxis_title="Amount (DKK)",
                height=300,
                showlegend=False,
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="white"),
                xaxis=dict(gridcolor="#333"),
                yaxis=dict(gridcolor="#333")
            )

            st.plotly_chart(fig_weekly, use_container_width=True)

        with col2:
            # Day of week spending
            dow_spending = df_payments.groupby('day_of_week')['amount_abs'].sum()
            dow_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            dow_spending = dow_spending.reindex(dow_order, fill_value=0)

            fig_dow = go.Figure(go.Bar(
                x=dow_spending.index,
                y=dow_spending.values,
                marker=dict(color='#357abd'),
                hovertemplate="<b>%{x}</b><br>Total: %{y:,.0f} DKK<extra></extra>"
            ))

            fig_dow.update_layout(
                title="Spending by Day of Week",
                xaxis_title="Day",
                yaxis_title="Amount (DKK)",
                height=300,
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="white"),
                xaxis=dict(gridcolor="#333"),
                yaxis=dict(gridcolor="#333")
            )

            st.plotly_chart(fig_dow, use_container_width=True)

        st.markdown("---")

    def _render_business_intelligence(self, df_payments: pd.DataFrame, df_vendors: pd.DataFrame, metrics: Dict):
        """Render business intelligence insights."""
        st.markdown("### Business Intelligence & Insights")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("#### Spending Patterns")

            # Peak spending day
            daily_avg = df_payments.groupby(df_payments['date'].dt.day_name())['amount_abs'].mean()
            peak_day = daily_avg.idxmax()
            st.metric("Peak Spending Day", peak_day, f"{daily_avg[peak_day]:,.0f} DKK avg")

            # Spending volatility
            monthly_std = metrics['monthly_spending'].std()
            monthly_mean = metrics['monthly_spending'].mean()
            volatility = (monthly_std / monthly_mean * 100) if monthly_mean > 0 else 0
            st.metric("Spending Volatility", f"{volatility:.1f}%", "Monthly variation")

        with col2:
            st.markdown("#### Vendor Relationships")

            # Vendor concentration
            top_5_vendors = df_payments.groupby('vendor_name')['amount_abs'].sum().nlargest(5).sum()
            concentration = (top_5_vendors / metrics['total_spent'] * 100)
            st.metric("Top 5 Vendor Share", f"{concentration:.1f}%", "of total spending")

            # New vendors this month
            if len(df_payments) > 0:
                current_month = df_payments['date'].max().to_period('M')
                new_vendors = df_payments[df_payments['year_month'] == current_month]['vendor_name'].nunique()
                st.metric("New Vendors (Current)", new_vendors, "this month")

        with col3:
            st.markdown("#### Financial Health")

            # Average days between transactions
            if len(df_payments) > 1:
                date_diffs = df_payments['date'].sort_values().diff().dt.days.dropna()
                avg_days = date_diffs.mean()
                st.metric("Avg Transaction Frequency", f"{avg_days:.1f} days", "between transactions")

            # Largest single transaction
            max_transaction = df_payments['amount_abs'].max()
            st.metric("Largest Transaction", f"{max_transaction:,.0f} DKK", f"{(max_transaction/metrics['avg_transaction']):.1f}x avg")

        # Advanced insights
        st.markdown("#### Key Insights")

        insights = []

        # Spending trend
        if len(metrics['monthly_spending']) >= 2:
            recent_trend = metrics['monthly_spending'].iloc[-2:].pct_change().iloc[-1]
            if recent_trend > 0.1:
                insights.append(f"📈 Spending increased by {recent_trend*100:.1f}% last month")
            elif recent_trend < -0.1:
                insights.append(f"📉 Spending decreased by {abs(recent_trend)*100:.1f}% last month")

        # High-value vendors
        expensive_vendors = df_payments.groupby('vendor_name')['amount_abs'].mean()
        if len(expensive_vendors) > 0:
            top_expensive = expensive_vendors.nlargest(1)
            insights.append(f"💰 Highest average transaction: {top_expensive.index[0]} ({top_expensive.iloc[0]:,.0f} DKK)")

        # Transaction patterns
        weekend_spending = df_payments[df_payments['date'].dt.dayofweek >= 5]['amount_abs'].sum()
        weekday_spending = df_payments[df_payments['date'].dt.dayofweek < 5]['amount_abs'].sum()
        if weekend_spending > weekday_spending * 0.3:  # More than 30% of weekday spending
            insights.append(f"🎯 Significant weekend activity: {weekend_spending:,.0f} DKK ({weekend_spending/(weekend_spending+weekday_spending)*100:.1f}%)")

        for insight in insights[:3]:  # Show top 3 insights
            st.info(insight)

        st.markdown("---")


def render_analytics_page(processor):
    """Entry point for rendering the Analytics page."""
    page = AnalyticsPage(processor)
    page.render()