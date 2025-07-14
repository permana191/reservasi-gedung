from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
import os
from dotenv import load_dotenv  

load_dotenv() 

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'kunci_rahasia_sistem_reservasi')

# Konfigurasi Database SQLite
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///seminar_reservation.db').replace('postgres://', 'postgresql://')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Model Database
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    nama = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='user')
    reservations = db.relationship('Reservation', backref='user', lazy=True)

    def __repr__(self):
        return f'<User {self.username}>'

class Reservation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    ruangan_id = db.Column(db.String(10), nullable=False) # R001, R002, etc.
    nama_kegiatan = db.Column(db.String(200), nullable=False)
    tanggal = db.Column(db.String(10), nullable=False) # YYYY-MM-DD
    waktu_mulai = db.Column(db.String(5), nullable=False) # HH:MM
    waktu_selesai = db.Column(db.String(5), nullable=False) # HH:MM
    peserta = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='Menunggu') # Menunggu, Disetujui, Ditolak

    def __repr__(self):
        return f'<Reservation {self.nama_kegiatan} in {self.ruangan_id}>'

# Data ruangan (tetap di memori karena statis)
ruangan = {
    'R001': {'nama': 'Seminar A', 'kapasitas': 50, 'fasilitas': 'Proyektor, AC, Podium'},
    'R002': {'nama': 'Seminar B', 'kapasitas': 30, 'fasilitas': 'Proyektor, Whiteboard'},
    'R003': {'nama': 'Seminar C', 'kapasitas': 100, 'fasilitas': 'Proyektor, AC, Sound System'}
}

# Fungsi untuk inisialisasi database dan data awal
def init_db():
    with app.app_context():
        db.create_all()

        # Tambahkan user default jika belum ada
        if not User.query.filter_by(username='admin').first():
            admin_user = User(username='admin', password='admin123', nama='Admin', role='admin')
            db.session.add(admin_user)
        if not User.query.filter_by(username='user1').first():
            regular_user = User(username='user1', password='user123', nama='User ', role='user')
            db.session.add(regular_user)
        db.session.commit()

        # Tambahkan reservasi default jika belum ada
        if not Reservation.query.first():
            user1_obj = User.query.filter_by(username='user1').first()
            if user1_obj:
                res1 = Reservation(user_id=user1_obj.id, ruangan_id='R001', nama_kegiatan='Workshop Python', tanggal='2023-11-15', waktu_mulai='09:00', waktu_selesai='12:00', peserta=30, status='Disetujui')
                res2 = Reservation(user_id=user1_obj.id, ruangan_id='R002', nama_kegiatan='Meeting Proyek', tanggal='2023-11-16', waktu_mulai='10:00', waktu_selesai='11:00', peserta=10, status='Menunggu')
                db.session.add_all([res1, res2])
                db.session.commit()

@app.route('/')
def index():
    return render_template('index.html', ruangan=ruangan)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username, password=password).first()
        if user:
            session['user_id'] = user.id
            session['username'] = user.username
            session['nama'] = user.nama
            session['role'] = user.role
            flash('Login berhasil!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Username atau password salah!', 'danger')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        nama = request.form['nama']
        
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username sudah terdaftar!', 'danger')
        elif len(username) < 4:
            flash('Username minimal 4 karakter!', 'danger')
        elif len(password) < 6:
            flash('Password minimal 6 karakter!', 'danger')
        else:
            new_user = User(username=username, password=password, nama=nama, role='user')
            db.session.add(new_user)
            db.session.commit()
            flash('Registrasi berhasil! Silakan login.', 'success')
            return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    user_reservations = Reservation.query.filter_by(user_id=session['user_id']).order_by(Reservation.id.desc()).limit(3).all()
    return render_template('dashboard.html', 
                           username=session['username'],
                           nama=session['nama'],
                           reservations=user_reservations,
                           ruangan=ruangan)

@app.route('/reservasi', methods=['GET', 'POST'])
def reservasi():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        ruangan_id = request.form['ruangan']
        nama_kegiatan = request.form['nama_kegiatan']
        tanggal = request.form['tanggal']
        waktu_mulai = request.form['waktu_mulai']
        waktu_selesai = request.form['waktu_selesai']
        peserta = int(request.form['peserta'])
        
        # Validasi
        if ruangan_id not in ruangan:
            flash('Ruangan tidak valid!', 'danger')
        elif peserta > ruangan[ruangan_id]['kapasitas']:
            flash(f'Jumlah peserta melebihi kapasitas ruangan! (Maks: {ruangan[ruangan_id]["kapasitas"]})', 'danger')
        elif waktu_mulai >= waktu_selesai:
            flash('Waktu selesai harus setelah waktu mulai!', 'danger')
        else:
            # Cek konflik reservasi
            conflicting_reservations = Reservation.query.filter(
                Reservation.ruangan_id == ruangan_id,
                Reservation.tanggal == tanggal,
                Reservation.status.in_(['Menunggu', 'Disetujui']), # Hanya cek dengan reservasi yang aktif
                Reservation.waktu_mulai < waktu_selesai,
                Reservation.waktu_selesai > waktu_mulai
            ).first()
            
            if conflicting_reservations:
                flash('Ruangan sudah dipesan pada waktu tersebut!', 'danger')
            else:
                new_reservation = Reservation(
                    user_id=session['user_id'],
                    ruangan_id=ruangan_id,
                    nama_kegiatan=nama_kegiatan,
                    tanggal=tanggal,
                    waktu_mulai=waktu_mulai,
                    waktu_selesai=waktu_selesai,
                    peserta=peserta,
                    status='Menunggu'
                )
                db.session.add(new_reservation)
                db.session.commit()
                flash('Reservasi berhasil diajukan!', 'success')
                return redirect(url_for('status'))
    
    return render_template('reservasi.html', ruangan=ruangan)

@app.route('/status')
def status():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    user_reservations = Reservation.query.filter_by(user_id=session['user_id']).order_by(Reservation.tanggal.desc(), Reservation.waktu_mulai.desc()).all()
    return render_template('status.html', reservations=user_reservations, ruangan=ruangan)

@app.route('/admin')
def admin():
    if 'username' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
    
    all_reservations = Reservation.query.order_by(Reservation.tanggal.desc(), Reservation.waktu_mulai.desc()).all()
    all_users = User.query.all()
    users_for_template = all_users # Langsung gunakan list objek User

    return render_template('admin.html', 
                           reservations=all_reservations,
                           ruangan=ruangan,
                           users=users_for_template)

@app.route('/approve/<int:reservation_id>')
def approve(reservation_id):
    if 'username' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
    
    res = Reservation.query.get(reservation_id)
    if res:
        res.status = 'Disetujui'
        db.session.commit()
        flash(f'Reservasi #{reservation_id} telah disetujui!', 'success')
    else:
        flash(f'Reservasi #{reservation_id} tidak ditemukan!', 'danger')
    
    return redirect(url_for('admin'))

@app.route('/reject/<int:reservation_id>')
def reject(reservation_id):
    if 'username' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))

    res = Reservation.query.get(reservation_id)
    if res:
        res.status = 'Ditolak'
        db.session.commit()
        flash(f'Reservasi #{reservation_id} telah ditolak!', 'success')
    else:
        flash(f'Reservasi #{reservation_id} tidak ditemukan!', 'danger')
    
    return redirect(url_for('admin'))

@app.route('/delete/<int:reservation_id>')
def delete(reservation_id):
    if 'username' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
    
    res = Reservation.query.get(reservation_id)
    if res:
        db.session.delete(res)
        db.session.commit()
        flash(f'Reservasi #{reservation_id} telah dihapus!', 'success')
    else:
        flash(f'Reservasi #{reservation_id} tidak ditemukan!', 'danger')
    return redirect(url_for('admin'))

@app.route('/logout')
def logout():
    session.clear()
    flash('Anda telah logout.', 'info')
    return redirect(url_for('index'))

# Rute baru untuk detail ruangan
@app.route('/ruangan/<ruangan_id>')
def detail_ruangan(ruangan_id):
    if ruangan_id not in ruangan:
        flash('Ruangan tidak ditemukan!', 'danger')
        return redirect(url_for('index'))
    
    room_info = ruangan[ruangan_id]
    room_reservations = Reservation.query.filter_by(ruangan_id=ruangan_id).order_by(Reservation.tanggal.desc(), Reservation.waktu_mulai.desc()).all()
    
    return render_template('detail_ruangan.html', 
                           ruangan_id=ruangan_id,
                           ruangan=room_info,
                           reservations=room_reservations)

if __name__ == '__main__':
    with app.app_context():
        init_db()  # ⬅️ Tambahkan baris ini

    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
