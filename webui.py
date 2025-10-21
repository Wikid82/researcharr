from flask import Flask, render_template_string, request, redirect, url_for, flash, jsonify
import yaml
import os
import requests

CONFIG_PATH = '/config/config.yml'

app = Flask(__name__)
app.secret_key = 'researcharr_secret_key'

SETTINGS_FORM = '''
<!doctype html>
<title>researcharr Settings</title>
<h2>researcharr Settings</h2>
<form method="post" action="/save">
  <fieldset><legend>General</legend>
    PUID: <input name="puid" value="{{ researcharr.puid }}"><br>
    PGID: <input name="pgid" value="{{ researcharr.pgid }}"><br>
    Timezone: <input name="timezone" value="{{ researcharr.timezone }}"><br>
    Cron Schedule: <input name="cron_schedule" value="{{ researcharr.cron_schedule }}"><br>
  </fieldset>
  <fieldset><legend>Radarr</legend>
    Process: <input name="radarr_process" type="checkbox" {% if radarr.process %}checked{% endif %}><br>
    URL: <input name="radarr_url" value="{{ radarr.url }}"><br>
    API Key: <input name="radarr_api_key" value="{{ radarr.api_key }}"><br>
    Movies to Upgrade: <input name="radarr_movies_to_upgrade" value="{{ radarr.movies_to_upgrade }}"><br>
    <button type="button" onclick="testConnection('radarr')">Test Radarr Connection</button>
    <span id="radarr_status"></span>
  </fieldset>
  <fieldset><legend>Sonarr</legend>
    Process: <input name="sonarr_process" type="checkbox" {% if sonarr.process %}checked{% endif %}><br>
    URL: <input name="sonarr_url" value="{{ sonarr.url }}"><br>
    API Key: <input name="sonarr_api_key" value="{{ sonarr.api_key }}"><br>
    Episodes to Upgrade: <input name="sonarr_episodes_to_upgrade" value="{{ sonarr.episodes_to_upgrade }}"><br>
    <button type="button" onclick="testConnection('sonarr')">Test Sonarr Connection</button>
    <span id="sonarr_status"></span>
  </fieldset>
  <br><input type="submit" value="Save Settings">
</form>
<script>
function testConnection(service) {
  fetch('/test_connection/' + service)
    .then(r => r.json())
    .then(data => {
      document.getElementById(service + '_status').innerText = data.status;
    });
}
</script>
'''

def load_config():
    with open(CONFIG_PATH, 'r') as f:
        return yaml.safe_load(f)

def save_config(cfg):
    with open(CONFIG_PATH, 'w') as f:
        yaml.safe_dump(cfg, f)

@app.route('/', methods=['GET'])
def index():
    cfg = load_config()
    return render_template_string(SETTINGS_FORM,
        researcharr=cfg.get('researcharr', {}),
        radarr=cfg.get('radarr', {}),
        sonarr=cfg.get('sonarr', {}))

@app.route('/save', methods=['POST'])
def save():
    cfg = load_config()
    # General
    cfg['researcharr']['puid'] = int(request.form.get('puid', 1000))
    cfg['researcharr']['pgid'] = int(request.form.get('pgid', 1000))
    cfg['researcharr']['timezone'] = request.form.get('timezone', 'America/New_York')
    cfg['researcharr']['cron_schedule'] = request.form.get('cron_schedule', '0 */1 * * *')
    # Radarr
    cfg['radarr']['process'] = 'radarr_process' in request.form
    cfg['radarr']['url'] = request.form.get('radarr_url', '')
    cfg['radarr']['api_key'] = request.form.get('radarr_api_key', '')
    cfg['radarr']['movies_to_upgrade'] = int(request.form.get('radarr_movies_to_upgrade', 5))
    # Sonarr
    cfg['sonarr']['process'] = 'sonarr_process' in request.form
    cfg['sonarr']['url'] = request.form.get('sonarr_url', '')
    cfg['sonarr']['api_key'] = request.form.get('sonarr_api_key', '')
    cfg['sonarr']['episodes_to_upgrade'] = int(request.form.get('sonarr_episodes_to_upgrade', 5))
    save_config(cfg)
    flash('Settings saved!')
    return redirect(url_for('index'))

@app.route('/test_connection/<service>')
def test_connection(service):
    cfg = load_config()
    if service == 'radarr':
        url = cfg['radarr'].get('url', '')
        key = cfg['radarr'].get('api_key', '')
    elif service == 'sonarr':
        url = cfg['sonarr'].get('url', '')
        key = cfg['sonarr'].get('api_key', '')
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

if __name__ == '__main__':
  app.run(host='0.0.0.0', port=2929, debug=True)
