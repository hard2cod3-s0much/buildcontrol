from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from datetime import datetime
from pathlib import Path
from functools import wraps

app = Flask(__name__)
app.secret_key = 'buildcontrol-secret-key-2026'

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / 'data'
DATA_DIR.mkdir(exist_ok=True)
FILES_DIR = DATA_DIR / 'uploads'
FILES_DIR.mkdir(exist_ok=True)

USERS = [
    {'id': 1, 'username': 'admin', 'password': 'admin123', 'role': 'admin'},
    {'id': 2, 'username': 'manager', 'password': 'manager123', 'role': 'manager'},
    {'id': 3, 'username': 'logist', 'password': 'logist123', 'role': 'logist'},
    {'id': 4, 'username': 'director', 'password': 'director123', 'role': 'director'},
]

ORDERS = []
MATERIALS = []
SERVICES = []
STATUS_HISTORY = []

next_order_id = 1
next_material_id = 1
next_service_id = 1

class User(UserMixin):
    def __init__(self, uid, username, role):
        self.id = uid
        self.username = username
        self.role = role
    
    def is_admin(self):
        return self.role == 'admin'
    
    def is_manager(self):
        return self.role in ['admin', 'manager']
    
    def is_logist(self):
        return self.role in ['admin', 'logist']
    
    def is_director(self):
        return self.role in ['admin', 'director']

@login_manager.user_loader
def load_user(user_id):
    for u in USERS:
        if str(u['id']) == str(user_id):
            return User(u['id'], u['username'], u['role'])
    return None

def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('login'))
            if current_user.role not in roles:
                flash('Недостаточно прав доступа', 'danger')
                return redirect(url_for('index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

ORDER_STATUSES = ['Разрешения', 'Фундамент', 'Каркас', 'Контур/Крыша', 'Отделка', 'Готов']
STATUS_REQUIREMENTS = {
    'Фундамент': ['Бетон', 'Арматура'],
    'Каркас': ['Бетон', 'Арматура', 'Доска'],
    'Контур/Крыша': ['Бетон', 'Арматура', 'Доска', 'Кровля'],
    'Отделка': ['Бетон', 'Арматура', 'Доска', 'Кровля', 'Штукатурка'],
}

AVAILABLE_SERVICES = [
    {'name': 'Дизайн интерьера', 'price': 50000},
    {'name': 'Доставка мебели', 'price': 15000},
    {'name': 'Монтаж сигнализации', 'price': 25000},
    {'name': 'Охрана объекта', 'price': 10000},
]

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    stats = {
        'total_orders': len(ORDERS),
        'in_progress': len([o for o in ORDERS if o['status'] != 'Готов']),
        'completed': len([o for o in ORDERS if o['status'] == 'Готов']),
        'total_materials': sum(m['quantity'] for m in MATERIALS),
        'total_services': len(SERVICES),
        'total_revenue': sum(o.get('total_cost', 0) for o in ORDERS if o['status'] == 'Готов')
    }
    return render_template('index.html', stats=stats, orders=ORDERS[:5])

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username').strip()
        password = request.form.get('password').strip()
        
        for u in USERS:
            if u['username'] == username and u['password'] == password:
                user = User(u['id'], u['username'], u['role'])
                login_user(user)
                flash('Вход выполнен как ' + u['role'], 'success')
                return redirect(url_for('dashboard'))
        flash('Неверный логин или пароль', 'danger')
        return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('login'))

@app.route('/orders')
@login_required
def orders_list():
    return render_template('orders_list.html', orders=ORDERS)

@app.route('/order/create', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'manager')
def order_create():
    global next_order_id
    if request.method == 'POST':
        file_path = None
        if 'file' in request.files:
            file = request.files['file']
            if file and file.filename:
                filename = 'order_' + str(next_order_id) + '_' + file.filename
                file_path = str(FILES_DIR / filename)
                file.save(file_path)
        
        ORDERS.append({
            'id': next_order_id,
            'name': request.form['name'],
            'address': request.form['address'],
            'client': request.form['client'],
            'status': 'Разрешения',
            'plan_date': request.form['plan_date'],
            'created_at': datetime.now().strftime('%Y-%m-%d'),
            'created_by': current_user.username,
            'file_path': file_path,
            'materials_required': [],
            'services': [],
            'total_cost': 0
        })
        next_order_id += 1
        flash('Заказ создан', 'success')
        return redirect(url_for('orders_list'))
    return render_template('order_form.html', services=AVAILABLE_SERVICES)

@app.route('/order/<int:order_id>')
@login_required
def order_detail(order_id):
    order = next((o for o in ORDERS if o['id'] == order_id), None)
    if not order:
        flash('Заказ не найден', 'danger')
        return redirect(url_for('orders_list'))
    history = [h for h in STATUS_HISTORY if h['order_id'] == order_id]
    return render_template('order_detail.html', order=order, statuses=ORDER_STATUSES, history=history)

@app.route('/order/<int:order_id>/update_status', methods=['POST'])
@login_required
@role_required('admin', 'manager')
def order_update_status(order_id):
    order = next((o for o in ORDERS if o['id'] == order_id), None)
    if not order:
        flash('Заказ не найден', 'danger')
        return redirect(url_for('orders_list'))
    
    new_status = request.form['status']
    current_idx = ORDER_STATUSES.index(order['status'])
    new_idx = ORDER_STATUSES.index(new_status)
    
    if new_idx > current_idx and new_status in STATUS_REQUIREMENTS:
        required_materials = STATUS_REQUIREMENTS[new_status]
        reserved_materials = [m['name'] for m in MATERIALS if m.get('reserved', 0) > 0]
        missing = [m for m in required_materials if m not in reserved_materials]
        if missing:
            flash('Нельзя перейти на этап. Не хватает материалов: ' + ', '.join(missing), 'warning')
            return redirect(url_for('order_detail', order_id=order_id))
    
    order['status'] = new_status
    STATUS_HISTORY.append({
        'order_id': order_id,
        'old_status': ORDER_STATUSES[current_idx] if current_idx >= 0 else 'Новый',
        'new_status': new_status,
        'changed_by': current_user.username,
        'changed_at': datetime.now().strftime('%Y-%m-%d %H:%M')
    })
    flash('Статус изменён на: ' + new_status, 'success')
    return redirect(url_for('order_detail', order_id=order_id))

@app.route('/order/<int:order_id>/add_service', methods=['POST'])
@login_required
@role_required('admin', 'manager')
def order_add_service(order_id):
    order = next((o for o in ORDERS if o['id'] == order_id), None)
    if not order:
        flash('Заказ не найден', 'danger')
        return redirect(url_for('orders_list'))
    
    service_name = request.form.get('service')
    service = next((s for s in AVAILABLE_SERVICES if s['name'] == service_name), None)
    if service:
        order['services'].append(service['name'])
        order['total_cost'] += service['price']
        flash('Услуга добавлена', 'success')
    return redirect(url_for('order_detail', order_id=order_id))

@app.route('/warehouse', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'logist')
def warehouse():
    global next_material_id
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add':
            MATERIALS.append({
                'id': next_material_id,
                'name': request.form['name'],
                'unit': request.form['unit'],
                'quantity': int(request.form['quantity']),
                'reserved': 0,
                'supplier': request.form.get('supplier', 'Не указан'),
                'delivery_date': request.form.get('delivery_date', datetime.now().strftime('%Y-%m-%d')),
                'last_updated': datetime.now().strftime('%Y-%m-%d')
            })
            next_material_id += 1
            flash('Материалы добавлены на склад', 'success')
        elif action == 'reserve':
            material_id = int(request.form['material_id'])
            order_id = int(request.form['order_id'])
            quantity = int(request.form['quantity'])
            material = next((m for m in MATERIALS if m['id'] == material_id), None)
            order = next((o for o in ORDERS if o['id'] == order_id), None)
            if material and order:
                if material['quantity'] - material['reserved'] >= quantity:
                    material['reserved'] += quantity
                    order['materials_required'].append({'name': material['name'], 'quantity': quantity})
                    flash('Зарезервировано для заказа', 'success')
                else:
                    flash('Недостаточно материала на складе', 'danger')
    return render_template('warehouse.html', materials=MATERIALS, orders=ORDERS)

@app.route('/services')
@login_required
def services():
    return render_template('services.html', services=SERVICES, available=AVAILABLE_SERVICES)

@app.route('/service/add', methods=['POST'])
@login_required
@role_required('admin', 'manager')
def service_add():
    global next_service_id
    service_name = request.form.get('service')
    service = next((s for s in AVAILABLE_SERVICES if s['name'] == service_name), None)
    if service:
        SERVICES.append({
            'id': next_service_id,
            'name': service['name'],
            'price': service['price'],
            'added_by': current_user.username,
            'added_at': datetime.now().strftime('%Y-%m-%d')
        })
        next_service_id += 1
        flash('Услуга добавлена', 'success')
    return redirect(url_for('services'))

@app.route('/reports')
@login_required
@role_required('admin', 'director')
def reports():
    return render_template('reports.html', orders=ORDERS, materials=MATERIALS, services=SERVICES)

@app.route('/export/orders')
@login_required
@role_required('admin', 'director', 'manager')
def export_orders():
    from io import StringIO
    output = StringIO()
    output.write("ID;Объект;Адрес;Клиент;Статус;Дата;Стоимость\n")
    for o in ORDERS:
        output.write(str(o['id']) + ';' + o['name'] + ';' + o['address'] + ';' + o['client'] + ';' + o['status'] + ';' + o['plan_date'] + ';' + str(o.get('total_cost', 0)) + '\n')
    
    return (output.getvalue(), 200, {
        'Content-Type': 'text/csv; charset=utf-8',
        'Content-Disposition': 'attachment; filename=orders_report.csv'
    })

@app.route('/export/tax')
@login_required
@role_required('admin', 'director')
def export_tax():
    from io import StringIO
    output = StringIO()
    total_revenue = sum(o.get('total_cost', 0) for o in ORDERS if o['status'] == 'Готов')
    vat = total_revenue * 0.20
    profit_tax = total_revenue * 0.20
    total_tax = vat + profit_tax
    
    output.write("Период;Доход;НДС 20%;Налог на прибыль 20%;Итого налогов\n")
    output.write(datetime.now().strftime('%Y-%m') + ';' + str(total_revenue) + ';' + str(vat) + ';' + str(profit_tax) + ';' + str(total_tax) + '\n')
    
    return (output.getvalue(), 200, {
        'Content-Type': 'text/csv; charset=utf-8',
        'Content-Disposition': 'attachment; filename=tax_report.csv'
    })

@app.route('/export/statistics')
@login_required
@role_required('admin', 'director')
def export_statistics():
    from io import StringIO
    output = StringIO()
    output.write("Показатель;Значение\n")
    output.write('Всего заказов;' + str(len(ORDERS)) + '\n')
    output.write('Завершено;' + str(len([o for o in ORDERS if o['status'] == 'Готов'])) + '\n')
    output.write('В работе;' + str(len([o for o in ORDERS if o['status'] != 'Готов'])) + '\n')
    output.write('Материалов на складе;' + str(sum(m['quantity'] for m in MATERIALS)) + '\n')
    output.write('Общая выручка;' + str(sum(o.get('total_cost', 0) for o in ORDERS if o['status'] == 'Готов')) + '\n')
    
    return (output.getvalue(), 200, {
        'Content-Type': 'text/csv; charset=utf-8',
        'Content-Disposition': 'attachment; filename=statistics_report.csv'
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)