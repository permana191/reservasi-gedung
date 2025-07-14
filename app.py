from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'kunci_rahasia_sistem_reservasi'

# Database sederhana
users = {
    'admin': {'password': 'admin123', 'nama': 'admin', 'role': 'admin'},
    'user1': {'password': 'user123', 'nama': 'User', 'role': 'user'}
}

ruangan = {
    'R001': {'nama': 'Seminar A', 'kapasitas': 50, 'fasilitas': 'Proyektor, AC, Podium'},
    'R002': {'nama': 'Seminar B', 'kapasitas': 30, 'fasilitas': 'Proyektor, Whiteboard'},
    'R003': {'nama': 'Seminar C', 'kapasitas': 100, 'fasilitas': 'Proyektor, AC, Sound System'}
}

reservations = [
    {
        'id': 1,
        'username': 'user1',
        'ruangan': 'R001',
        'nama_kegiatan': 'Workshop Python',
        'tanggal': '2023-11-15',
        'waktu_mulai': '09:00',
        'waktu_selesai': '12:00',
        'peserta': 30,
        'status': 'Disetujui'
    }
]

@app.route('/')
def index():
    return render_template('index.html', ruangan=ruangan)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if username in users and users[username]['password'] == password:
            session['username'] = username
            session['nama'] = users[username]['nama']
            session['role'] = users[username]['role']
            flash('Login berhasil!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Username atau password salah!', 'danger')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        nama = request.form['nama']
        
        if username in users:
            flash('Username sudah terdaftar!', 'danger')
        elif len(username) < 4:
            flash('Username minimal 4 karakter!', 'danger')
        elif len(password) < 6:
            flash('Password minimal 6 karakter!', 'danger')
        else:
            users[username] = {'password': password, 'nama': nama, 'role': 'user'}
            flash('Registrasi berhasil! Silakan login.', 'success')
            return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    user_reservations = [r for r in reservations if r['username'] == session['username']]
    return render_template('dashboard.html', 
                         username=session['username'],
                         nama=session['nama'],
                         reservations=user_reservations[:3])

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
            conflict = False
            for res in reservations:
                if res['ruangan'] == ruangan_id and res['tanggal'] == tanggal:
                    if (waktu_mulai < res['waktu_selesai'] and waktu_selesai > res['waktu_mulai']):
                        conflict = True
                        break
            
            if conflict:
                flash('Ruangan sudah dipesan pada waktu tersebut!', 'danger')
            else:
                new_reservation = {
                    'id': len(reservations) + 1,
                    'username': session['username'],
                    'ruangan': ruangan_id,
                    'nama_kegiatan': nama_kegiatan,
                    'tanggal': tanggal,
                    'waktu_mulai': waktu_mulai,
                    'waktu_selesai': waktu_selesai,
                    'peserta': peserta,
                    'status': 'Menunggu'
                }
                reservations.append(new_reservation)
                flash('Reservasi berhasil diajukan!', 'success')
                return redirect(url_for('status'))
    
    return render_template('reservasi.html', ruangan=ruangan)

@app.route('/status')
def status():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    user_reservations = [r for r in reservations if r['username'] == session['username']]
    return render_template('status.html', reservations=user_reservations)

@app.route('/admin')
def admin():
    if 'username' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
    
    return render_template('admin.html', 
                         reservations=reservations,
                         ruangan=ruangan,
                         users=users)

@app.route('/approve/<int:reservation_id>')
def approve(reservation_id):
    if 'username' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
    
    for res in reservations:
        if res['id'] == reservation_id:
            res['status'] = 'Disetujui'
            flash(f'Reservasi #{reservation_id} telah disetujui!', 'success')
            break
    
    return redirect(url_for('admin'))

@app.route('/reject/<int:reservation_id>')
def reject(reservation_id):
    if 'username' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
    
    for res in reservations:
        if res['id'] == reservation_id:
            res['status'] = 'Ditolak'
            flash(f'Reservasi #{reservation_id} telah ditolak!', 'success')
            break
    
    return redirect(url_for('admin'))

@app.route('/delete/<int:reservation_id>')
def delete(reservation_id):
    if 'username' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
    
    global reservations
    reservations = [res for res in reservations if res['id'] != reservation_id]
    flash(f'Reservasi #{reservation_id} telah dihapus!', 'success')
    return redirect(url_for('admin'))

@app.route('/logout')
def logout():
    session.clear()
    flash('Anda telah logout.', 'info')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)