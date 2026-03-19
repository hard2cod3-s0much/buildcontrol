from flask import Flask, render_template, request, redirect, url_for, flash, send_file
import pandas as pd
from pathlib import Path
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = 'buildcontrol-secret-key-2026'

DATA_DIR = Path(__file__).parent / 'data'
DATA_DIR.mkdir(exist_ok=True)

class ExcelDB:
    @staticmethod
    def get_orders():
        file = DATA_DIR / 'orders.xlsx'
        if not file.exists():
            df = pd.DataFrame(columns=['id', 'name', 'address', 'client', 'status', 'plan_date', 'created_at'])
            df.to_excel(file, index=False)
            return []
        df = pd.read_excel(file)
        return df.to_dict('records')
    
    @staticmethod
    def add_order(name, address, client, plan_date):
        file = DATA_DIR / 'orders.xlsx'
        df = pd.read_excel(file) if file.exists() else pd.DataFrame(columns=['id', 'name', 'address', 'client', 'status', 'plan_date', 'created_at'])
        new_id = int(df['id'].max()) + 1 if not df.empty else 1
        new_order = {
            'id': new_id, 'name': name, 'address': address, 'client': client,
            'status': 'Разрешения', 'plan_date': plan_date, 'created_at': datetime.now().strftime('%Y-%m-%d')
        }
        df = pd.concat([df, pd.DataFrame([new_order])], ignore_index=True)
        df.to_excel(file, index=False)
        return new_id
    
    @staticmethod
    def get_order(order_id):
        orders = ExcelDB.get_orders()
        for o in orders:
            if o['id'] == order_id:
                return o
        return None
    
    @staticmethod
    def update_status(order_id, new_status):
        file = DATA_DIR / 'orders.xlsx'
        df = pd.read_excel(file)
        idx = df[df['id'] == order_id].index
        if len(idx) > 0:
            df.loc[idx[0], 'status'] = new_status
            df.to_excel(file, index=False)
            return True
        return False
    
    @staticmethod
    def get_materials():
        file = DATA_DIR / 'materials.xlsx'
        if not file.exists():
            df = pd.DataFrame(columns=['id', 'name', 'unit', 'quantity', 'reserved'])
            df.to_excel(file, index=False)
            return []
        df = pd.read_excel(file)
        return df.to_dict('records')
    
    @staticmethod
    def add_material(name, unit, quantity):
        file = DATA_DIR / 'materials.xlsx'
        df = pd.read_excel(file) if file.exists() else pd.DataFrame(columns=['id', 'name', 'unit', 'quantity', 'reserved'])
        idx = df[df['name'] == name].index
        if len(idx) > 0:
            df.loc[idx[0], 'quantity'] += quantity
        else:
            new_id = int(df['id'].max()) + 1 if not df.empty else 1
            new_mat = {'id': new_id, 'name': name, 'unit': unit, 'quantity': quantity, 'reserved': 0}
            df = pd.concat([df, pd.DataFrame([new_mat])], ignore_index=True)
        df.to_excel(file, index=False)
        return True

@app.route('/')
def index():
    orders = ExcelDB.get_orders()
    stats = {
        'total': len(orders),
        'in_progress': len([o for o in orders if o['status'] != 'Готов']),
        'completed': len([o for o in orders if o['status'] == 'Готов'])
    }
    return render_template('index.html', stats=stats, orders=orders[:5])

@app.route('/orders')
def orders_list():
    orders = ExcelDB.get_orders()
    return render_template('orders.html', orders=orders)

@app.route('/order/create', methods=['GET', 'POST'])
def order_create():
    if request.method == 'POST':
        ExcelDB.add_order(
            name=request.form['name'],
            address=request.form['address'],
            client=request.form['client'],
            plan_date=request.form['plan_date']
        )
        flash(' Заказ создан!', 'success')
        return redirect(url_for('orders_list'))
    return render_template('order_form.html')

@app.route('/order/<int:order_id>')
def order_detail(order_id):
    order = ExcelDB.get_order(order_id)
    if not order:
        flash(' Заказ не найден', 'danger')
        return redirect(url_for('orders_list'))
    statuses = ['Разрешения', 'Фундамент', 'Каркас', 'Контур/Крыша', 'Отделка', 'Готов']
    return render_template('order_detail.html', order=order, statuses=statuses)

@app.route('/order/<int:order_id>/update_status', methods=['POST'])
def order_update_status(order_id):
    new_status = request.form['status']
    if ExcelDB.update_status(order_id, new_status):
        flash(f' Статус изменён на: {new_status}', 'success')
    return redirect(url_for('order_detail', order_id=order_id))

@app.route('/warehouse', methods=['GET', 'POST'])
def warehouse():
    if request.method == 'POST':
        ExcelDB.add_material(
            name=request.form['name'],
            unit=request.form['unit'],
            quantity=int(request.form['quantity'])
        )
        flash(' Материал добавлен!', 'success')
        return redirect(url_for('warehouse'))
    materials = ExcelDB.get_materials()
    return render_template('warehouse.html', materials=materials)

@app.route('/export')
def export():
    orders = ExcelDB.get_orders()
    df = pd.DataFrame(orders)
    file = DATA_DIR / 'report.xlsx'
    df.to_excel(file, index=False)
    return send_file(file, as_attachment=True, download_name='report.xlsx')

if __name__ == '__main__':
    app.run(debug=True, port=5000)