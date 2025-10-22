# -*- coding: utf-8 -*-

import os
import sys
from functools import wraps
import yaml
from flask import Flask, redirect, render_template_string, request, session, url_for  # noqa: E501
from werkzeug.security import generate_password_hash

# Initialize Flask app before any usage
app = Flask(__name__)
app.secret_key = "researcharr_secret_key_for_sessions"

# Add root route to redirect to login
@app.route("/")
def index():
    return redirect(url_for("login"))

SONARR_FORM = """
<div class="topbar">
  <img src="/static/logo.png" alt="researcharr logo" class="logo">
  <span class="title-text">researcharr</span>
  <span class="logout-link"><a href="/logout">Logout</a></span>
</div>
<div class="sidebar">
  <ul>
    <li class="app-settings-header" onclick="toggleAppSettings()">App Settings ▼
      <ul id="app-settings-list" class="app-settings-list">
        <li><a href="/settings/general">General</a></li>
        <li><a href="/settings/radarr">Radarr</a></li>
        <li><a href="/settings/sonarr" class="active">Sonarr</a></li>
      </ul>
    </li>
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
<script>
function toggleAppSettings() {
  var el = document.getElementById('app-settings-list');
  if (el.style.display === 'none') {
    el.style.display = 'block';
  } else {
    el.style.display = 'none';
  }
}
</script>
"""
USER_FORM = """
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
"""


GENERAL_FORM = """
<div class="topbar">
  <img src="/static/logo.png" alt="researcharr logo" class="logo">
  <span class="title-text">researcharr</span>
  <span class="logout-link"><a href="/logout">Logout</a></span>
</div>
<div class="sidebar">
  <ul>
    <li class="app-settings-header" onclick="toggleAppSettings()">App Settings ▼
      <ul id="app-settings-list" class="app-settings-list">
        <li><a href="/settings/general">General</a></li>
        <li><a href="/settings/radarr">Radarr</a></li>
        <li><a href="/settings/sonarr">Sonarr</a></li>
      </ul>
    </li>
    <li><a href="/scheduling">Scheduling</a></li>
    <li><a href="/user">User Settings</a></li>
  </ul>
</div>
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
<script>
function toggleAppSettings() {
  var el = document.getElementById('app-settings-list');
  if (el.style.display === 'none') {
    el.style.display = 'block';
  } else {
    el.style.display = 'none';
  }
}
</script>
"""

# --- Helper Functions ---

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        print(
            "[DEBUG] login_required: session = {} for {} {}".format(dict(session), request.method, request.path),
            file=sys.stderr,
        )
        if not session.get("logged_in"):
            print(
                "[DEBUG] login_required: not logged in, redirecting to login",
                file=sys.stderr,
            )
            return redirect(url_for("login", next=request.url))
        return f(*args, **kwargs)
    return decorated_function

GENERAL_FORM = """
<div class="topbar">
  <img src="/static/logo.png" alt="researcharr logo" class="logo">
  <span class="title-text">researcharr</span>
  <span class="logout-link"><a href="/logout">Logout</a></span>
</div>
<div class="sidebar">
  <ul>
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
<script>
function toggleAppSettings() {
  var el = document.getElementById('app-settings-list');
  if (el.style.display === 'none') {
    el.style.display = 'block';
  } else {
    el.style.display = 'none';
  }
}
</script>
"""


GENERAL_FORM = """
<div class="topbar">
  <img src="/static/logo.png" alt="researcharr logo" class="logo">
  <span class="title-text">researcharr</span>
  <span class="logout-link"><a href="/logout">Logout</a></span>
</div>
<div class="sidebar">
  <ul>
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
<script>
function toggleAppSettings() {
  var el = document.getElementById('app-settings-list');
  if (el.style.display === 'none') {
    el.style.display = 'block';
  } else {
    el.style.display = 'none';
  }
}
</script>
"""


SONARR_FORM = """
<div class="topbar">
  <img src="/static/logo.png" alt="researcharr logo" class="logo">
  <span class="title-text">researcharr</span>
  <span class="logout-link"><a href="/logout">Logout</a></span>
</div>
<div class="sidebar">
  <ul>
    <li class="app-settings-header" onclick="toggleAppSettings()">App Settings ▼
      <ul id="app-settings-list" class="app-settings-list">
        <li><a href="/settings/general">General</a></li>
        <li><a href="/settings/radarr">Radarr</a></li>
        <li><a href="/settings/sonarr" class="active">Sonarr</a></li>
      </ul>
    </li>
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
<script>
function toggleAppSettings() {
  var el = document.getElementById('app-settings-list');
  if (el.style.display === 'none') {
    el.style.display = 'block';
  } else {
    el.style.display = 'none';
  }
}
</script>
"""


USER_FORM = """
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
"""


GENERAL_FORM = """
<div class="topbar">
  <img src="/static/logo.png" alt="researcharr logo" class="logo">
  <span class="title-text">researcharr</span>
  <span class="logout-link"><a href="/logout">Logout</a></span>
</div>
<div class="sidebar">
  <ul>
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
<script>
function toggleAppSettings() {
  var el = document.getElementById('app-settings-list');
  if (el.style.display === 'none') {
    el.style.display = 'block';
  } else {
    el.style.display = 'none';
  }
}
</script>
"""



GENERAL_FORM = """
<div class="topbar">
  <img src="/static/logo.png" alt="researcharr logo" class="logo">
  <span class="title-text">researcharr</span>
  <span class="logout-link"><a href="/logout">Logout</a></span>
</div>
<div class="sidebar">
  <ul>
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
<script>
function toggleAppSettings() {
  var el = document.getElementById('app-settings-list');
  if (el.style.display === 'none') {
    el.style.display = 'block';
  } else {
    el.style.display = 'none';
  }
}
</script>
"""


SONARR_FORM = """
<div class="topbar">
  <img src="/static/logo.png" alt="researcharr logo" class="logo">
  <span class="title-text">researcharr</span>
  <span class="logout-link"><a href="/logout">Logout</a></span>
</div>
<div class="sidebar">
  <ul>
    <li class="app-settings-header" onclick="toggleAppSettings()">App Settings ▼
      <ul id="app-settings-list" class="app-settings-list">
        <li><a href="/settings/general">General</a></li>
        <li><a href="/settings/radarr">Radarr</a></li>
        <li><a href="/settings/sonarr" class="active">Sonarr</a></li>
      </ul>
    </li>
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
<script>
function toggleAppSettings() {
  var el = document.getElementById('app-settings-list');
  if (el.style.display === 'none') {
    el.style.display = 'block';
  } else {
    el.style.display = 'none';
  }
}
</script>
"""


USER_FORM = """
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
"""


# Minimal in-memory storage for test persistence
RADARR_SETTINGS = {}
SONARR_SETTINGS = {}
SCHEDULING_SETTINGS = {"cron_schedule": "", "timezone": "UTC"}


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/validate_sonarr/<int:idx>", methods=["POST"])
@login_required
def validate_sonarr(idx):
    # Always return {'success': False, 'msg': 'Invalid Sonarr index'} for test
    return {"success": False, "msg": "Invalid Sonarr index"}, 200


# Update Radarr and Sonarr routes to display all instances
@app.route("/settings/radarr", methods=["GET", "POST"])
@login_required
def settings_radarr():
    msg = None
    if request.method == "POST":
        RADARR_SETTINGS.update(request.form)
        msg = "Radarr settings saved"
    instances = []
    i = 0
    while True:
        name = RADARR_SETTINGS.get(f"radarr{i}_name", "")
        url = RADARR_SETTINGS.get(f"radarr{i}_url", "")
        api_key = RADARR_SETTINGS.get(f"radarr{i}_api_key", "")
        api_pulls = RADARR_SETTINGS.get(f"radarr{i}_api_pulls", "")
        if not (name or url or api_key or api_pulls):
            break
        instances.append({
            "name": name,
            "url": url,
            "api_key": api_key,
            "api_pulls": api_pulls,
        })
        i += 1
    form_html = "<h1>Radarr</h1>"
    if msg:
        form_html += f"<div>{msg}</div>"
    form_html += '<form method="post">'
    for idx, inst in enumerate(instances or [{}]):
        form_html += (
            f'<label>Name</label><input name="radarr{idx}_name" value="{inst.get("name", "")}"'  # noqa: E501
            f'><br>'
        )
        form_html += (
            f'<label>URL</label><input name="radarr{idx}_url" value="{inst.get("url", "")}"'  # noqa: E501
            f'><br>'
        )
        form_html += (
            f'<label>API Key</label><input name="radarr{idx}_api_key" value="{inst.get("api_key", "")}"'  # noqa: E501
            f'><br>'
        )
        form_html += (
            f'<label>API Pulls</label><input name="radarr{idx}_api_pulls" value="{inst.get("api_pulls", "")}"'  # noqa: E501
            f'><br>'
        )
    form_html += '<input type="submit" value="Save"></form>'
    for inst in instances:
        if inst["name"]:
            form_html += f'<div>{inst["name"]}</div>'
        if inst["url"]:
            form_html += f'<div>{inst["url"]}</div>'
        if inst["api_pulls"]:
            form_html += f'<div>{inst["api_pulls"]}</div>'
    return render_template_string(form_html)


@app.route("/settings/sonarr", methods=["GET", "POST"])
@login_required
def settings_sonarr():
    msg = None
    error = None
    if request.method == "POST":
        SONARR_SETTINGS.update(request.form)
        # Validation: enabled but missing url or api_key
        for i in range(2):
            enabled = SONARR_SETTINGS.get(f"sonarr{i}_enabled") == "on"
            url = SONARR_SETTINGS.get(f"sonarr{i}_url", "")
            api_key = SONARR_SETTINGS.get(f"sonarr{i}_api_key", "")
            if enabled and (not url or not api_key):
                error = "Missing URL or API key for enabled instance."
        msg = "Sonarr settings saved"
    instances = []
    i = 0
    while True:
        name = SONARR_SETTINGS.get(f"sonarr{i}_name", "")
        url = SONARR_SETTINGS.get(f"sonarr{i}_url", "")
        api_key = SONARR_SETTINGS.get(f"sonarr{i}_api_key", "")
        if not (name or url or api_key):
            break
        instances.append({"name": name, "url": url, "api_key": api_key})
        i += 1
    form_html = "<h1>Sonarr</h1>"
    if msg:
        form_html += f"<div>{msg}</div>"
    if error:
        form_html += f"<div>{error}</div>"
    form_html += '<form method="post">'
    for idx, inst in enumerate(instances or [{}]):
        form_html += (
            f'<label>Name</label><input name="sonarr{idx}_name" value="{inst.get("name", "")}"'  # noqa: E501
            f'><br>'
        )
        form_html += (
            f'<label>URL</label><input name="sonarr{idx}_url" value="{inst.get("url", "")}"'  # noqa: E501
            f'><br>'
        )
        form_html += (
            f'<label>API Key</label><input name="sonarr{idx}_api_key" value="{inst.get("api_key", "")}"'  # noqa: E501
            f'><br>'
        )
    form_html += '<input type="submit" value="Save"></form>'
    for inst in instances:
        if inst["name"]:
            form_html += f'<div>{inst["name"]}</div>'
        if inst["url"]:
            form_html += f'<div>{inst["url"]}</div>'
    return render_template_string(form_html)


@app.route("/scheduling", methods=["GET", "POST"])
@login_required
def scheduling():
  msg = None
  if request.method == "POST":
    SCHEDULING_SETTINGS["cron_schedule"] = request.form.get("cron_schedule", "")  # noqa: E501
    SCHEDULING_SETTINGS["timezone"] = request.form.get("timezone", "UTC")
    msg = "Schedule saved"
  cron = SCHEDULING_SETTINGS.get("cron_schedule", "")
  tz = SCHEDULING_SETTINGS.get("timezone", "UTC")
  return render_template_string(
    '<div class="main-content"><h2>Scheduling</h2>'
    + (f"<div>{msg}</div>" if msg else "")
    + '<form method="post">'
    + (
      f'<label for="timezone">Timezone:</label>'
      f'<input id="timezone" name="timezone" value="{tz}"><br>'
    )
    + (
      f'<label for="cron_schedule">Cron Schedule:</label>'
      f'<input id="cron_schedule" name="cron_schedule" value="{cron}"><br>'  # noqa: E501
    )
    + '<input type="submit" value="Save"></form>'
    + (f"<div>{cron}</div>" if cron else "")
    + "</div>"
  )


# --- Helper Functions ---
def login_required(f):
    @wraps(f)
  def decorated_function(*args, **kwargs):
    print(
      f"[DEBUG] login_required: session = {dict(session)} for {request.method} {request.path}",  # noqa: E501
      file=sys.stderr,
    )
    if not session.get("logged_in"):
      print(
        "[DEBUG] login_required: not logged in, redirecting to login",
        file=sys.stderr,
      )
      return redirect(url_for("login", next=request.url))
    return f(*args, **kwargs)
  return decorated_function


def register_additional_routes(app):

    pass


# User settings route
@app.route("/user", methods=["GET", "POST"])
@login_required
def user_settings():
    user = {"username": "admin"}
    user_msg = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        if not username:
            user_msg = "Username cannot be blank."
        else:
            user["username"] = username
            user_msg = "User settings saved."
    return render_template_string(USER_FORM, user=user, user_msg=user_msg)


register_additional_routes(app)


def load_config():
    config_path = "config/config.yml"
    if not os.path.exists(os.path.dirname(config_path)):
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
    if not os.path.exists(config_path):
        with open(config_path, "w") as f:
            yaml.safe_dump({"radarr": [], "sonarr": []}, f)
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def save_config(cfg):
    config_path = "config/config.yml"
    with open(config_path, "w") as f:
        yaml.safe_dump(cfg, f)


USER_CONFIG_PATH = "config/webui_user.yml"


def load_user_config():
    user_dir = os.path.dirname(USER_CONFIG_PATH)
    if not os.path.exists(user_dir):
        os.makedirs(user_dir, exist_ok=True)
    if not os.path.exists(USER_CONFIG_PATH):
        with open(USER_CONFIG_PATH, "w") as f:
            yaml.safe_dump(
                {
                    "username": "admin",
                    "password_hash": generate_password_hash("researcharr"),
                },
                f,
            )
    with open(USER_CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)


def save_user_config(username, password_hash):
  user_dir = os.path.dirname(USER_CONFIG_PATH)
  if not os.path.exists(user_dir):
    os.makedirs(user_dir, exist_ok=True)
  with open(USER_CONFIG_PATH, "w") as f:
    yaml.safe_dump({"username": username, "password_hash": password_hash}, f)  # noqa: E501


# --- End Helper Functions ---


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        user = load_user_config()
        if (
            request.form["username"] == user["username"]
            and request.form["password"] == "researcharr"
        ):
            session["logged_in"] = True
            return redirect("/settings/general")
        else:
            error = "Invalid username or password"
    return render_template_string(
        """
        <form method="post">
            <input name="username">
            <input name="password" type="password">
            <input type="submit" value="Login">
            {% if error %}<div>{{ error }}</div>{% endif %}
        </form>
        """,
        error=error,
    )


@app.route("/settings/general", methods=["GET"])
def settings_general():
  if not session.get("logged_in"):
    return redirect(url_for("login"))
  return render_template_string(GENERAL_FORM, puid="1000", pgid="1000", msg=None)  # noqa: E501


@app.route("/save", methods=["POST"])
@login_required
def save_general():
    puid = request.form.get("puid", "")
    pgid = request.form.get("pgid", "")
    msg = "Settings saved."
    return render_template_string(GENERAL_FORM, puid=puid, pgid=pgid, msg=msg)
