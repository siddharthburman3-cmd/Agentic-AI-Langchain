import streamlit as st
import re
import json
from datetime import datetime
from collections import defaultdict

# File to store expenses
EXPENSE_FILE = 'expenses.json'

CATEGORIES = ['food', 'travel', 'investment', 'charity', 'shopping']
CATEGORY_KEYWORDS = {
    'food': ['food', 'groceries', 'restaurant', 'lunch', 'dinner', 'breakfast', 'snack'],
    'travel': ['travel', 'taxi', 'uber', 'bus', 'train', 'flight', 'cab', 'commute'],
    'investment': ['investment', 'stocks', 'mutual fund', 'sip', 'shares', 'crypto'],
    'charity': ['charity', 'donation', 'help', 'ngo'],
    'shopping': ['shopping', 'clothes', 'electronics', 'gadget', 'mall', 'purchase']
}

def load_expenses():
    try:
        with open(EXPENSE_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_expenses(expenses):
    with open(EXPENSE_FILE, 'w') as f:
        json.dump(expenses, f, indent=2)

def classify_category(description):
    desc = description.lower()
    for cat, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in desc:
                return cat
    return 'other'

def parse_expense(text):
    # Extract amount
    amount_match = re.search(r'(\d+(?:\.\d{1,2})?)', text)
    amount = float(amount_match.group(1)) if amount_match else 0.0
    # Extract date (today if not found)
    date = datetime.today().strftime('%Y-%m-%d')
    # Classify category
    category = classify_category(text)
    return {'amount': amount, 'category': category, 'date': date, 'description': text}

def add_expense(text):
    expenses = load_expenses()
    entry = parse_expense(text)
    expenses.append(entry)
    save_expenses(expenses)
    return entry

def summarize_expenses(expenses):
    summary = defaultdict(float)
    for e in expenses:
        summary[e['category']] += e['amount']
    return summary

def monthly_expenses(expenses):
    monthly = defaultdict(float)
    for e in expenses:
        month = e['date'][:7]
        monthly[month] += e['amount']
    return monthly

# Streamlit UI

st.title('Expense Tracker Agent')
st.write('Log your expenses in natural language. Example: "Spent 200 on groceries today"')


# Structured single entry with all fields
st.subheader('Add Expense (Structured Fields)')
with st.form('structured_expense'):
    date = st.date_input('Date', datetime.today())
    amount = st.number_input('Amount', min_value=0.0, step=1.0)
    category = st.selectbox('Category', CATEGORIES + ['other'])
    description = st.text_input('Description')
    submit_structured = st.form_submit_button('Add Expense')
    if submit_structured:
        entry = {
            'date': date.strftime('%Y-%m-%d'),
            'amount': amount,
            'category': category,
            'description': description
        }
        expenses = load_expenses()
        expenses.append(entry)
        save_expenses(expenses)
        st.success('Expense added! Please reload the page.')

with st.form('log_expense'):
    expense_text = st.text_input('Enter expense:')
    submitted = st.form_submit_button('Log Expense')
    if submitted and expense_text:
        entry = add_expense(expense_text)
        st.success(f"Logged: {entry}")

expenses = load_expenses()
if expenses:
    st.subheader('All Expenses')
    edited = False
    deleted = False
    for idx, exp in enumerate(expenses):
        col1, col2, col3 = st.columns([4, 1, 1])
        with col1:
            st.write(f"{exp['date']} | ‚Çπ{exp['amount']} | {exp['category']} | {exp['description']}")
        with col2:
            if st.button('Edit', key=f'edit_{idx}'):
                with st.form(f'edit_form_{idx}'):
                    new_date = st.text_input('Date', exp['date'])
                    new_amount = st.number_input('Amount', value=float(exp['amount']))
                    new_category = st.selectbox('Category', CATEGORIES + ['other'], index=(CATEGORIES + ['other']).index(exp['category']) if exp['category'] in (CATEGORIES + ['other']) else 0)
                    new_desc = st.text_input('Description', exp['description'])
                    save_edit = st.form_submit_button('Save')
                    if save_edit:
                        expenses[idx] = {'date': new_date, 'amount': new_amount, 'category': new_category, 'description': new_desc}
                        save_expenses(expenses)
                        st.success('Expense updated! Please reload the page.')
                        edited = True
        with col3:
            if st.button('Delete', key=f'del_{idx}'):
                expenses.pop(idx)
                save_expenses(expenses)
                st.success('Expense deleted! Please reload the page.')
                deleted = True
                break

    if not edited and not deleted:
        st.subheader('Visualization Options')
        viz_option = st.radio('Choose visualization:', [
            'Expense per Month',
            'Expense per Day',
            'Expense per Category'
        ])

        if viz_option == 'Expense per Month':
            st.subheader('Monthly Expenses')
            monthly = monthly_expenses(expenses)
            st.bar_chart(monthly)
        elif viz_option == 'Expense per Day':
            st.subheader('Daily Expenses')
            # Aggregate by day
            daily = defaultdict(float)
            for e in expenses:
                daily[e['date']] += e['amount']
            st.bar_chart(daily)
        elif viz_option == 'Expense per Category':
            st.subheader('Category-wise Expenses')
            summary = summarize_expenses(expenses)
            st.bar_chart(summary)

        # Suggestions
        summary = summarize_expenses(expenses)
        if summary.get('investment', 0) < max(summary.get(cat, 0) for cat in summary if cat != 'investment'):
            st.warning('Consider increasing your investment and reducing other expenses!')
else:
    st.info('No expenses logged yet.')

