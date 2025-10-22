GENERAL_FORM = '''
<div class="main-content">
<form method="post" action="/settings/general">
  <fieldset><legend>General Settings</legend>
    PUID: <input name="puid" value="{{ puid }}"><br>
    PGID: <input name="pgid" value="{{ pgid }}"><br>
    <input type="submit" value="Save General Settings">
    {% if msg %}<div class="user-msg">{{ msg }}</div>{% endif %}
  </fieldset>
</form>
</div>
'''

from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import yaml
from flask import Flask, render_template_string, request, redirect, url_for, flash, jsonify, session
import os
import requests

app = Flask(__name__)

GENERAL_FORM = '''
<div class="main-content">
<form method="post" action="/settings/general">
  <fieldset><legend>General Settings</legend>
    PUID: <input name="puid" value="{{ puid }}"><br>
    PGID: <input name="pgid" value="{{ pgid }}"><br>
    <input type="submit" value="Save General Settings">
    {% if msg %}<div class="user-msg">{{ msg }}</div>{% endif %}
  </fieldset>
</form>
</div>
'''

RADARR_FORM = '''
<div class="topbar">
  <img src="/static/logo.png" alt="researcharr logo" class="logo">
  <span class="title-text">researcharr</span>
  <span class="logout-link"><a href="/logout">Logout</a></span>
</div>
<div class="sidebar">
  <ul>
    <li><a href="/settings/general">General</a></li>
    <li><a href="/settings/radarr" class="active">Radarr</a></li>
    <li><a href="/settings/sonarr">Sonarr</a></li>
    <li><a href="/scheduling">Scheduling</a></li>
    <li><a href="/user">User Settings</a></li>
  </ul>
</div>
<div class="main-content">
{% if validate_summary %}<div class="user-msg">{{ validate_summary }}</div>{% endif %}
<form method="post" action="/settings/radarr">
  <fieldset><legend>Radarr Instances</legend>
    {% for i in range(5) %}
      <fieldset style="margin:10px; border:1px solid #ccc;">
        <legend>Radarr {{i+1}}</legend>
        Enable: <label class="switch"><input name="radarr{{i}}_enabled" type="checkbox" {% if radarr[i].enabled %}checked{% endif %} onchange="toggleInstance('radarr', {{i}})"><span class="slider round"></span></label><br>
        <div id="radarr_fields_{{i}}" class="instance-fields{% if radarr[i].enabled %} open{% endif %}">
          Name: <input name="radarr{{i}}_name" value="{{ radarr[i].name }}"><br>
          URL: <input name="radarr{{i}}_url" value="{{ radarr[i].url }}"><br>
          API Key: <input name="radarr{{i}}_api_key" value="{{ radarr[i].api_key }}"><br>
          Process: <input name="radarr{{i}}_process" type="checkbox" {% if radarr[i].get('process', False) %}checked{% endif %}><br>
          API Pulls per Hour: <input name="radarr{{i}}_api_pulls" value="{{ radarr[i].get('api_pulls', 20) }}" style="width:60px;"> <small>(default: 20)</small><br>
          Enable State Management: <input name="radarr{{i}}_state_mgmt" type="checkbox" {% if radarr[i].get('state_mgmt', True) %}checked{% endif %}><br>
          Movies to Upgrade: <input name="radarr{{i}}_movies_to_upgrade" value="{{ radarr[i].movies_to_upgrade }}"><br>
          Max Download Queue: <input name="radarr{{i}}_max_download_queue" value="{{ radarr[i].max_download_queue if radarr[i].get('max_download_queue') is not none else 15 }}"><br>
          Reprocess Interval (days): <input name="radarr{{i}}_reprocess_interval_days" value="{{ radarr[i].reprocess_interval_days if radarr[i].get('reprocess_interval_days') is not none else 7 }}"><br>
          <button type="button" onclick="testConnection('radarr', {{i}})">Test Connection</button>
          <button type="button" onclick="validateRadarr({{i}})">Validate & Save</button>
          <span id="radarr_status_{{i}}" class="test-result"></span>
          <span id="radarr_validate_{{i}}" class="validate-result"></span>
        </div>
      </fieldset>
    {% endfor %}
  </fieldset>
  <br><input type="submit" value="Save Radarr Settings">
  </form>
</div>
'''

SONARR_FORM = '''
<div class="topbar">
  <img src="/static/logo.png" alt="researcharr logo" class="logo">
  <span class="title-text">researcharr</span>
  <span class="logout-link"><a href="/logout">Logout</a></span>
</div>
<div class="sidebar">
  <ul>
    <li><a href="/settings/general">General</a></li>
    <li><a href="/settings/radarr">Radarr</a></li>
    <li><a href="/settings/sonarr" class="active">Sonarr</a></li>
    <li><a href="/scheduling">Scheduling</a></li>
    <li><a href="/user">User Settings</a></li>
  </ul>
</div>
<div class="main-content">
{% if validate_summary %}<div class="user-msg">{{ validate_summary }}</div>{% endif %}
<form method="post" action="/settings/sonarr">
  <fieldset><legend>Sonarr Instances</legend>
    {% for i in range(5) %}
      <fieldset style="margin:10px; border:1px solid #ccc;">
        <legend>Sonarr {{i+1}}</legend>
        Enable: <label class="switch"><input name="sonarr{{i}}_enabled" type="checkbox" {% if sonarr[i].enabled %}checked{% endif %} onchange="toggleInstance('sonarr', {{i}})"><span class="slider round"></span></label><br>
        <div id="sonarr_fields_{{i}}" class="instance-fields{% if sonarr[i].enabled %} open{% endif %}">
          Name: <input name="sonarr{{i}}_name" value="{{ sonarr[i].name }}"><br>
          URL: <input name="sonarr{{i}}_url" value="{{ sonarr[i].url }}"><br>
          API Key: <input name="sonarr{{i}}_api_key" value="{{ sonarr[i].api_key }}"><br>
          Process: <input name="sonarr{{i}}_process" type="checkbox" {% if sonarr[i].get('process', False) %}checked{% endif %}><br>
          Process by: <select name="sonarr{{i}}_mode">
            <option value="series" {% if sonarr[i].get('mode', 'series') == 'series' %}selected{% endif %}>Series (default, most efficient)</option>
            <option value="season" {% if sonarr[i].get('mode') == 'season' %}selected{% endif %}>Season</option>
            <option value="episode" {% if sonarr[i].get('mode') == 'episode' %}selected{% endif %}>Episode</option>
          </select><br>
          API Pulls per Hour: <input name="sonarr{{i}}_api_pulls" value="{{ sonarr[i].get('api_pulls', 20) }}" style="width:60px;"> <small>(default: 20)</small><br>
          Enable State Management: <input name="sonarr{{i}}_state_mgmt" type="checkbox" {% if sonarr[i].get('state_mgmt', True) %}checked{% endif %}><br>
          Episodes to Upgrade: <input name="sonarr{{i}}_episodes_to_upgrade" value="{{ sonarr[i].episodes_to_upgrade }}"><br>
          Max Download Queue: <input name="sonarr{{i}}_max_download_queue" value="{{ sonarr[i].max_download_queue if sonarr[i].get('max_download_queue') is not none else 15 }}"><br>
          Reprocess Interval (days): <input name="sonarr{{i}}_reprocess_interval_days" value="{{ sonarr[i].reprocess_interval_days if sonarr[i].get('reprocess_interval_days') is not none else 7 }}"><br>
          <button type="button" onclick="testConnection('sonarr', {{i}})">Test Connection</button>
          <button type="button" onclick="validateSonarr({{i}})">Validate & Save</button>
          <span id="sonarr_status_{{i}}" class="test-result"></span>
          <span id="sonarr_validate_{{i}}" class="validate-result"></span>
        </div>
      </fieldset>
    {% endfor %}
  </fieldset>
  <br><input type="submit" value="Save Sonarr Settings">
  </form>
</div>
'''

USER_FORM = '''
<div class="main-content">
<form method="post" action="/user">
  <fieldset><legend>User Settings</legend>
    Username: <input name="username" value="{{ user.username }}"><br>
    Password: <input name="password" type="password" placeholder="Leave blank to keep current"><br>
    <input type="submit" value="Save User Settings">
    {% if user_msg %}<div class="user-msg">{{ user_msg }}</div>{% endif %}
  </fieldset>
</form>
</div>
'''






# --- Helper Functions ---
def login_required(f):
  @wraps(f)
  def decorated_function(*args, **kwargs):
    import sys
    print(f"[DEBUG] login_required: session = {dict(session)} for {request.method} {request.path}", file=sys.stderr)
    if not session.get('logged_in'):
      print(f"[DEBUG] login_required: not logged in, redirecting to login", file=sys.stderr)
      return redirect(url_for('login', next=request.url))
    return f(*args, **kwargs)
  return decorated_function

def load_config():
  config_path = 'config/config.yml'
  if not os.path.exists(os.path.dirname(config_path)):
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
  if not os.path.exists(config_path):
    with open(config_path, 'w') as f:
      yaml.safe_dump({'radarr': [], 'sonarr': []}, f)
  with open(config_path, 'r') as f:
    return yaml.safe_load(f)

def save_config(cfg):
  config_path = 'config/config.yml'
  with open(config_path, 'w') as f:
    yaml.safe_dump(cfg, f)

USER_CONFIG_PATH = 'config/webui_user.yml'
def load_user_config():
  user_dir = os.path.dirname(USER_CONFIG_PATH)
  if not os.path.exists(user_dir):
    os.makedirs(user_dir, exist_ok=True)
  if not os.path.exists(USER_CONFIG_PATH):
    with open(USER_CONFIG_PATH, 'w') as f:
      yaml.safe_dump({'username': 'admin', 'password_hash': generate_password_hash('researcharr')}, f)
  with open(USER_CONFIG_PATH, 'r') as f:
    return yaml.safe_load(f)

def save_user_config(username, password_hash):
  user_dir = os.path.dirname(USER_CONFIG_PATH)
  if not os.path.exists(user_dir):
    os.makedirs(user_dir, exist_ok=True)
  with open(USER_CONFIG_PATH, 'w') as f:
    yaml.safe_dump({'username': username, 'password_hash': password_hash}, f)

# --- End Helper Functions ---

# Radarr Settings Page

@app.route('/settings/radarr', methods=['GET', 'POST'])
@login_required
def radarr_settings():
  cfg = load_config()
  radarr = cfg.get('radarr', [])
  while len(radarr) < 5:
    radarr.append({'enabled': False, 'name': f'Radarr {len(radarr)+1}', 'url': '', 'api_key': '', 'movies_to_upgrade': 5, 'max_download_queue': 15, 'reprocess_interval_days': 7, 'state_mgmt': True})
  user = load_user_config()
  from flask import get_flashed_messages
  messages = get_flashed_messages(with_categories=True)
  validate_summary = None
  for cat, msg in messages:
    if cat in ('error', 'validate', 'message'):
      validate_summary = msg
    else:
      validate_summary = msg
  if request.method == 'POST':
    import sys
    print(f"[DEBUG] Session at POST /settings/radarr: {dict(session)}", file=sys.stderr)
    new_radarr = []
    for i in range(5):
      enabled = f'radarr{i}_enabled' in request.form
      process = f'radarr{i}_process' in request.form
      state_mgmt = f'radarr{i}_state_mgmt' in request.form
      name = request.form.get(f'radarr{i}_name', f'Radarr {i+1}')
      url = request.form.get(f'radarr{i}_url', '')
      api_key = request.form.get(f'radarr{i}_api_key', '')
      api_pulls = int(request.form.get(f'radarr{i}_api_pulls', 20))
      new_radarr.append({
        'enabled': enabled,
        'process': process,
        'state_mgmt': state_mgmt,
        'name': name,
        'url': url,
        'api_key': api_key,
        'api_pulls': api_pulls,
        'movies_to_upgrade': int(request.form.get(f'radarr{i}_movies_to_upgrade', 5)),
        'max_download_queue': int(request.form.get(f'radarr{i}_max_download_queue', 15)),
        'reprocess_interval_days': int(request.form.get(f'radarr{i}_reprocess_interval_days', 7)),
      })
    # If any enabled instance is missing URL or API key, show error and do not save
    for inst in new_radarr:
      if inst['enabled'] and (not inst['url'] or not inst['api_key']):
        msg = 'Missing URL or API key for enabled instance.'
        print(f"[DEBUG] Returning error form, session: {dict(session)}", file=sys.stderr)
        flash(msg, 'error')
        return redirect(url_for('radarr_settings'))
    cfg['radarr'] = new_radarr
    save_config(cfg)
    flash('Radarr settings saved!')
    return redirect(url_for('radarr_settings'))
  # GET: show form, display flashed message if present
  messages = get_flashed_messages(with_categories=True)
  validate_summary = None
  for cat, msg in messages:
    if cat in ('error', 'validate', 'message'):
      validate_summary = msg
    else:
      validate_summary = msg
  return render_template_string(RADARR_FORM,
    radarr=radarr,
    active_tab='radarr',
    user=user,
    validate_summary=validate_summary)

# Sonarr Settings Page

@app.route('/settings/sonarr', methods=['GET', 'POST'])
@login_required
def sonarr_settings():
  cfg = load_config()
  sonarr = cfg.get('sonarr', [])
  while len(sonarr) < 5:
    sonarr.append({'enabled': False, 'name': f'Sonarr {len(sonarr)+1}', 'url': '', 'api_key': '', 'episodes_to_upgrade': 5, 'max_download_queue': 15, 'reprocess_interval_days': 7})
  user = load_user_config()
  from flask import get_flashed_messages
  messages = get_flashed_messages(with_categories=True)
  validate_summary = None
  for cat, msg in messages:
    if cat in ('error', 'validate', 'message'):
      validate_summary = msg
    else:
      validate_summary = msg
  from flask import get_flashed_messages
  if request.method == 'POST':
    import sys
    print(f"[DEBUG] Session at POST /settings/sonarr: {dict(session)}", file=sys.stderr)
    new_sonarr = []
    for i in range(5):
      enabled = f'sonarr{i}_enabled' in request.form
      process = f'sonarr{i}_process' in request.form
      mode = request.form.get(f'sonarr{i}_mode', 'series')
      api_pulls = int(request.form.get(f'sonarr{i}_api_pulls', 20))
      state_mgmt = f'sonarr{i}_state_mgmt' in request.form
      name = request.form.get(f'sonarr{i}_name', f'Sonarr {i+1}')
      url = request.form.get(f'sonarr{i}_url', '')
      api_key = request.form.get(f'sonarr{i}_api_key', '')
      new_sonarr.append({
        'enabled': enabled,
        'process': process,
        'mode': mode,
        'api_pulls': api_pulls,
        'state_mgmt': state_mgmt,
        'name': name,
        'url': url,
        'api_key': api_key,
        'episodes_to_upgrade': int(request.form.get(f'sonarr{i}_episodes_to_upgrade', 5)),
        'max_download_queue': int(request.form.get(f'sonarr{i}_max_download_queue', 15)),
        'reprocess_interval_days': int(request.form.get(f'sonarr{i}_reprocess_interval_days', 7)),
      })
    # If any enabled instance is missing URL or API key, show error and do not save
    for inst in new_sonarr:
      if inst['enabled'] and (not inst['url'] or not inst['api_key']):
        msg = 'Missing URL or API key for enabled instance.'
        print(f"[DEBUG] Returning error form, session: {dict(session)}", file=sys.stderr)
        flash(msg, 'error')
        return redirect(url_for('sonarr_settings'))
    cfg['sonarr'] = new_sonarr
    save_config(cfg)
    flash('Sonarr settings saved!')
    return redirect(url_for('sonarr_settings'))
  # GET: show form, display flashed message if present
  messages = get_flashed_messages(with_categories=True)
  validate_summary = None
  for cat, msg in messages:
    if cat in ('error', 'validate', 'message'):
      validate_summary = msg
    else:
      validate_summary = msg
  return render_template_string(SONARR_FORM,
    sonarr=sonarr,
    active_tab='sonarr',
    user=user,
    validate_summary=validate_summary)


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
  return render_template_string(USER_FORM,
    user=user,
    user_msg=msg,
    active_tab='user')



# Save endpoint for General settings form (legacy, for test compatibility)
@app.route('/save', methods=['POST'])
@login_required
def save():
  cfg = load_config()
  msg = None
  try:
    cfg.setdefault('researcharr', {})['puid'] = int(request.form.get('puid', 1000))
    cfg['researcharr']['pgid'] = int(request.form.get('pgid', 1000))
    save_config(cfg)
    msg = 'General settings saved!'
  except Exception as e:
    msg = f'Error: {e}'
  # After saving, show the General Settings page
  puid = cfg.get('researcharr', {}).get('puid', 1000)
  pgid = cfg.get('researcharr', {}).get('pgid', 1000)
  return render_template_string(GENERAL_FORM, puid=puid, pgid=pgid, msg=msg, active_tab='general')



@app.route('/validate_sonarr/<int:idx>', methods=['POST'])
@login_required
def validate_sonarr(idx):
  cfg = load_config()
  sonarr = cfg.get('sonarr', [])
  if idx < 0 or idx >= len(sonarr):
    return jsonify({'success': False, 'msg': 'Invalid Sonarr index'})
  inst = sonarr[idx]
  url = inst.get('url', '')
  key = inst.get('api_key', '')
  if url and not url.startswith(('http://', 'https://')):
    url = 'http://' + url
  if not url:
    return jsonify({'success': False, 'msg': 'Invalid or missing URL'})
  if not key:
    return jsonify({'success': False, 'msg': 'Missing API key'})
  # Test connection
  try:
    resp = requests.get(url.rstrip('/') + '/api/v3/system/status', headers={'Authorization': key}, timeout=10)
    if resp.status_code != 200:
      return jsonify({'success': False, 'msg': f'Connection failed: HTTP {resp.status_code}'})
  except Exception as e:
    return jsonify({'success': False, 'msg': f'Error: {e}'})
  # Simulate dry run (no actual changes)
  # (No-op for now)
  return jsonify({'success': True, 'msg': 'Connection successful (dry run)'})


from flask import Flask
app = Flask(__name__)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=2929, debug=True)
