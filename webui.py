
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import yaml

# --- User config file ---
USER_CONFIG_PATH = '/config/webui_user.yml'

def load_user_config():
  if not os.path.exists(USER_CONFIG_PATH):
    # Default user: admin/researcharr
    with open(USER_CONFIG_PATH, 'w') as f:
      yaml.safe_dump({
        'username': 'admin',
        'password_hash': generate_password_hash('researcharr')
      }, f)
  with open(USER_CONFIG_PATH, 'r') as f:
    return yaml.safe_load(f)

def save_user_config(username, password_hash):
  with open(USER_CONFIG_PATH, 'w') as f:
    yaml.safe_dump({'username': username, 'password_hash': password_hash}, f)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function
from flask import Flask, render_template_string, request, redirect, url_for, flash, jsonify, session
import yaml
import os
import requests

CONFIG_PATH = '/config/config.yml'

app = Flask(__name__)
app.secret_key = 'researcharr_secret_key'  # Change this in production

SETTINGS_FORM = '''
<!doctype html>
<title>researcharr Settings</title>
<div class="topbar">
  <img src="/static/logo.png" alt="researcharr logo" class="logo">
  <span class="title-text">researcharr</span>
  <span class="logout-link"><a href="/logout">Logout</a></span>
</div>
<div class="sidebar">
  <ul>
    <li><a href="/" {% if active_tab == 'app' %}class="active"{% endif %}>App Settings</a></li>
    <li><a href="/scheduling" {% if active_tab == 'scheduling' %}class="active"{% endif %}>Scheduling</a></li>
    <li><a href="/user" {% if active_tab == 'user' %}class="active"{% endif %}>User Settings</a></li>
  </ul>
</div>
<div class="main-content">
{% if active_tab == 'app' %}
<form method="post" action="/save">
  <fieldset><legend>General</legend>
    PUID: <input name="puid" value="{{ researcharr.puid }}"><br>
    PGID: <input name="pgid" value="{{ researcharr.pgid }}"><br>
    Timezone: <input name="timezone" value="{{ researcharr.timezone }}"><br>
  <!-- Cron Schedule field moved to Scheduling tab -->
  </fieldset>
  <fieldset><legend>Radarr Instances</legend>
    {% for i in range(5) %}
      <fieldset style="margin:10px; border:1px solid #ccc;">
        <legend>Radarr {{i+1}}</legend>
  Enable: <label class="switch"><input name="radarr{{i}}_enabled" type="checkbox" {% if radarr[i].enabled %}checked{% endif %}><span class="slider round"></span></label><br>
        Name: <input name="radarr{{i}}_name" value="{{ radarr[i].name }}"><br>
        URL: <input name="radarr{{i}}_url" value="{{ radarr[i].url }}"><br>
        API Key: <input name="radarr{{i}}_api_key" value="{{ radarr[i].api_key }}"><br>
  Movies to Upgrade: <input name="radarr{{i}}_movies_to_upgrade" value="{{ radarr[i].movies_to_upgrade }}"><br>
  Max Download Queue: <input name="radarr{{i}}_max_download_queue" value="{{ radarr[i].max_download_queue if radarr[i].get('max_download_queue') is not none else 15 }}"><br>
  Reprocess Interval (days): <input name="radarr{{i}}_reprocess_interval_days" value="{{ radarr[i].reprocess_interval_days if radarr[i].get('reprocess_interval_days') is not none else 7 }}"><br>
        <button type="button" onclick="testConnection('radarr', {{i}})">Test Connection</button>
        <span id="radarr_status_{{i}}"></span>
      </fieldset>
    {% endfor %}
  </fieldset>
  <fieldset><legend>Sonarr Instances</legend>
    {% for i in range(5) %}
      <fieldset style="margin:10px; border:1px solid #ccc;">
        <legend>Sonarr {{i+1}}</legend>
  Enable: <label class="switch"><input name="sonarr{{i}}_enabled" type="checkbox" {% if sonarr[i].enabled %}checked{% endif %}><span class="slider round"></span></label><br>
        Name: <input name="sonarr{{i}}_name" value="{{ sonarr[i].name }}"><br>
        URL: <input name="sonarr{{i}}_url" value="{{ sonarr[i].url }}"><br>
        API Key: <input name="sonarr{{i}}_api_key" value="{{ sonarr[i].api_key }}"><br>
  Episodes to Upgrade: <input name="sonarr{{i}}_episodes_to_upgrade" value="{{ sonarr[i].episodes_to_upgrade }}"><br>
  Max Download Queue: <input name="sonarr{{i}}_max_download_queue" value="{{ sonarr[i].max_download_queue if sonarr[i].get('max_download_queue') is not none else 15 }}"><br>
  Reprocess Interval (days): <input name="sonarr{{i}}_reprocess_interval_days" value="{{ sonarr[i].reprocess_interval_days if sonarr[i].get('reprocess_interval_days') is not none else 7 }}"><br>
        <button type="button" onclick="testConnection('sonarr', {{i}})">Test Connection</button>
        <span id="sonarr_status_{{i}}"></span>
      </fieldset>
    {% endfor %}
  </fieldset>
  <br><input type="submit" value="Save Settings">
  </form>
{% elif active_tab == 'scheduling' %}
<form method="post" action="/scheduling">
  <fieldset><legend>Cron Scheduling</legend>
    Cron Schedule: <input name="cron_schedule" value="{{ cron_schedule }}" style="width:220px;">
    <a href="https://crontab.guru/" target="_blank" style="margin-left:12px;">Cron Calculator</a><br>
    <small>Example: <code>0 */1 * * *</code> (every hour)</small><br>
    <input type="submit" value="Update Schedule">
    {% if sched_msg %}<div class="user-msg">{{ sched_msg }}</div>{% endif %}
  </fieldset>
</form>
{% elif active_tab == 'user' %}
<form method="post" action="/user">
  <fieldset><legend>User Settings</legend>
    Username: <input name="username" value="{{ user.username }}" required><br>
    New Password: <input type="password" name="password" placeholder="Leave blank to keep current"><br>
    <input type="submit" value="Update User">
    {% if user_msg %}<div class="user-msg">{{ user_msg }}</div>{% endif %}
  </fieldset>
</form>
{% endif %}
@app.route('/scheduling', methods=['GET', 'POST'])
@login_required
def scheduling():
  cfg = load_config()
  msg = None
  if request.method == 'POST':
    cron_schedule = request.form.get('cron_schedule', '').strip()
    if not cron_schedule:
      msg = 'Cron schedule cannot be blank.'
    else:
      cfg.setdefault('researcharr', {})['cron_schedule'] = cron_schedule
      save_config(cfg)
      msg = 'Cron schedule updated.'
      cfg = load_config()
  cron_schedule = cfg.get('researcharr', {}).get('cron_schedule', '0 */1 * * *')
  user = load_user_config()
  return render_template_string(SETTINGS_FORM,
    researcharr=None,
    radarr=None,
    sonarr=None,
    active_tab='scheduling',
    user=user,
    user_msg=None,
    cron_schedule=cron_schedule,
    sched_msg=msg)
</div>
<style>
body {
  background: linear-gradient(135deg, #5B6EF1 0%, #3B50C1 100%);
  font-family: 'Segoe UI', Arial, sans-serif;
  color: #2A3B8B;
  margin: 0;
  padding: 0;
}
.topbar {
  display: flex;
  align-items: center;
  background: #fff;
  padding: 18px 0 10px 0;
  box-shadow: 0 2px 8px rgba(42,59,139,0.07);
  margin-bottom: 0;
  justify-content: center;
  position: relative;
}
.logo {
  height: 48px;
  margin-right: 16px;
}
.title-text {
  font-size: 2.1em;
  font-weight: bold;
  color: #2A3B8B;
  letter-spacing: 2px;
}
.logout-link {
  position: absolute;
  right: 32px;
  top: 50%;
  transform: translateY(-50%);
  font-size: 1em;
}
.logout-link a {
  color: #2A3B8B;
  text-decoration: none;
  font-weight: bold;
  padding: 6px 16px;
  border-radius: 4px;
  background: #f7f8fd;
  border: 1px solid #3B50C1;
  transition: background 0.2s;
}
.logout-link a:hover {
  background: #e6eaff;
}
.sidebar {
  position: fixed;
  top: 80px;
  left: 0;
  width: 180px;
  height: 100%;
  background: #2A3B8B;
  color: #fff;
  padding-top: 24px;
  z-index: 10;
}
.sidebar ul {
  list-style: none;
  padding: 0;
  margin: 0;
}
.sidebar li {
  margin-bottom: 18px;
}
.sidebar a {
  color: #fff;
  text-decoration: none;
  font-size: 1.1em;
  padding: 8px 24px;
  display: block;
  border-radius: 4px 0 0 4px;
  transition: background 0.2s;
}
.sidebar a.active, .sidebar a:active {
  background: #5B6EF1;
  font-weight: bold;
}
.sidebar a:hover {
  background: #3B50C1;
}
.user-msg {
  color: #2A3B8B;
  margin-top: 12px;
  font-weight: bold;
}
.main-content {
  margin-left: 200px;
  padding: 32px 32px 24px 32px;
  background: #fff;
  border-radius: 12px;
  max-width: 800px;
  box-shadow: 0 4px 24px rgba(42,59,139,0.10);
  min-height: 80vh;
}
/* ...existing form and switch styles... */
.switch {
  position: relative;
  display: inline-block;
  width: 40px;
  height: 24px;
}
.switch input {display:none;}
.slider {
  position: absolute;
  cursor: pointer;
  top: 0; left: 0; right: 0; bottom: 0;
  background-color: #ccc;
  transition: .4s;
  border-radius: 24px;
}
.slider:before {
  position: absolute;
  content: "";
  height: 18px;
  width: 18px;
  left: 3px;
  bottom: 3px;
  background-color: white;
  transition: .4s;
  border-radius: 50%;
}
input:checked + .slider {
  background-color: #5B6EF1;
}
input:checked + .slider:before {
  transform: translateX(16px);
}
</style>
<script>
function testConnection(service, idx) {
  fetch('/test_connection/' + service + '/' + idx)
    .then(r => r.json())
    .then(data => {
      document.getElementById(service + '_status_' + idx).innerText = data.status;
    });
}
</script>
'''

def migrate_config(cfg):
  # Migrate radarr/sonarr from dict to list if needed
  if isinstance(cfg.get('radarr'), dict):
    r = cfg['radarr']
    cfg['radarr'] = [{
      'enabled': r.get('process', False),
      'name': r.get('name', 'Radarr 1'),
      'url': r.get('url', ''),
      'api_key': r.get('api_key', ''),
      'movies_to_upgrade': r.get('movies_to_upgrade', 5),
    }]
  if isinstance(cfg.get('sonarr'), dict):
    s = cfg['sonarr']
    cfg['sonarr'] = [{
      'enabled': s.get('process', False),
      'name': s.get('name', 'Sonarr 1'),
      'url': s.get('url', ''),
      'api_key': s.get('api_key', ''),
      'episodes_to_upgrade': s.get('episodes_to_upgrade', 5),
    }]
  return cfg

def load_config():
  with open(CONFIG_PATH, 'r') as f:
    cfg = yaml.safe_load(f)
  cfg = migrate_config(cfg)
  return cfg

def save_config(cfg):
    with open(CONFIG_PATH, 'w') as f:
        yaml.safe_dump(cfg, f)


@app.route('/', methods=['GET'])
@login_required
def index():
  cfg = load_config()
  # Pad radarr/sonarr lists to 5 for UI
  radarr = cfg.get('radarr', [])
  sonarr = cfg.get('sonarr', [])
  while len(radarr) < 5:
    radarr.append({'enabled': False, 'name': f'Radarr {len(radarr)+1}', 'url': '', 'api_key': '', 'movies_to_upgrade': 5, 'max_download_queue': 15, 'reprocess_interval_days': 7})
  while len(sonarr) < 5:
    sonarr.append({'enabled': False, 'name': f'Sonarr {len(sonarr)+1}', 'url': '', 'api_key': '', 'episodes_to_upgrade': 5, 'max_download_queue': 15, 'reprocess_interval_days': 7})
  user = load_user_config()
  return render_template_string(SETTINGS_FORM,
    researcharr=cfg.get('researcharr', {}),
    radarr=radarr,
    sonarr=sonarr,
    active_tab='app',
    user=user,
    user_msg=None)

@app.route('/user', methods=['GET', 'POST'])
@login_required
def user_settings():
  user = load_user_config()
  msg = None
  if request.method == 'POST':
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')
    if not username:
      msg = 'Username cannot be blank.'
    else:
      if password:
        password_hash = generate_password_hash(password)
      else:
        password_hash = user['password_hash']
      save_user_config(username, password_hash)
      msg = 'User settings updated.'
      user = load_user_config()
  return render_template_string(SETTINGS_FORM,
    researcharr=None,
    radarr=None,
    sonarr=None,
    active_tab='user',
    user=user,
    user_msg=msg)


@app.route('/save', methods=['POST'])
@login_required
def save():
  cfg = load_config()
  # General
  cfg['researcharr']['puid'] = int(request.form.get('puid', 1000))
  cfg['researcharr']['pgid'] = int(request.form.get('pgid', 1000))
  cfg['researcharr']['timezone'] = request.form.get('timezone', 'America/New_York')
  cfg['researcharr']['cron_schedule'] = request.form.get('cron_schedule', '0 */1 * * *')
  # Radarr
  radarr = []
  for i in range(5):
    radarr.append({
      'enabled': f'radarr{i}_enabled' in request.form,
      'name': request.form.get(f'radarr{i}_name', f'Radarr {i+1}'),
      'url': request.form.get(f'radarr{i}_url', ''),
      'api_key': request.form.get(f'radarr{i}_api_key', ''),
      'movies_to_upgrade': int(request.form.get(f'radarr{i}_movies_to_upgrade', 5)),
      'max_download_queue': int(request.form.get(f'radarr{i}_max_download_queue', 15)),
      'reprocess_interval_days': int(request.form.get(f'radarr{i}_reprocess_interval_days', 7)),
    })
  cfg['radarr'] = radarr
  # Sonarr
  sonarr = []
  for i in range(5):
    sonarr.append({
      'enabled': f'sonarr{i}_enabled' in request.form,
      'name': request.form.get(f'sonarr{i}_name', f'Sonarr {i+1}'),
      'url': request.form.get(f'sonarr{i}_url', ''),
      'api_key': request.form.get(f'sonarr{i}_api_key', ''),
      'episodes_to_upgrade': int(request.form.get(f'sonarr{i}_episodes_to_upgrade', 5)),
      'max_download_queue': int(request.form.get(f'sonarr{i}_max_download_queue', 15)),
      'reprocess_interval_days': int(request.form.get(f'sonarr{i}_reprocess_interval_days', 7)),
    })
  cfg['sonarr'] = sonarr
  save_config(cfg)
  flash('Settings saved!')
  return redirect(url_for('index'))


@app.route('/test_connection/<service>/<int:idx>')
@login_required
def test_connection(service, idx):
  cfg = load_config()
  if service == 'radarr':
    inst = cfg.get('radarr', [{}]*5)[idx]
    url = inst.get('url', '')
    key = inst.get('api_key', '')
  elif service == 'sonarr':
    inst = cfg.get('sonarr', [{}]*5)[idx]
    url = inst.get('url', '')
    key = inst.get('api_key', '')
  else:
    return jsonify({'status': 'Unknown service'})
  try:
    resp = requests.get(url + '/api/v3/system/status', headers={'Authorization': key}, timeout=10)
    if resp.status_code == 200:
      return jsonify({'status': 'Connection successful'})
    else:
      return jsonify({'status': f'Failed: HTTP {resp.status_code}'})
  except Exception as e:
    return jsonify({'status': f'Error: {e}'})

# --- Login page ---
LOGIN_FORM = '''
<!doctype html>
<title>Login - researcharr</title>
<div class="topbar">
  <img src="/static/logo.png" alt="researcharr logo" class="logo">
  <span class="title-text">researcharr</span>
</div>
<div class="login-content">
  <form method="post" action="/login">
    <fieldset>
      <legend>Login</legend>
      <label for="username">Username:</label><br>
      <input type="text" id="username" name="username" required><br>
      <label for="password">Password:</label><br>
      <input type="password" id="password" name="password" required><br>
      <input type="submit" value="Login">
      {% if error %}<div class="error">{{ error }}</div>{% endif %}
    </fieldset>
  </form>
</div>
<style>
.login-content {
  margin: 60px auto 0 auto;
  max-width: 400px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 4px 24px rgba(42,59,139,0.10);
  padding: 32px 32px 24px 32px;
}
.error {
  color: #b00;
  margin-top: 12px;
  font-weight: bold;
}
</style>
'''

@app.route('/login', methods=['GET', 'POST'])
def login():
  error = None
  user = load_user_config()
  if request.method == 'POST':
    username = request.form.get('username', '')
    password = request.form.get('password', '')
    if username == user['username'] and check_password_hash(user['password_hash'], password):
      session['logged_in'] = True
      return redirect(url_for('index'))
    else:
      error = 'Invalid username or password.'
  return render_template_string(LOGIN_FORM, error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
  app.run(host='0.0.0.0', port=2929, debug=True)
