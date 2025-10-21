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
  <fieldset><legend>Radarr Instances</legend>
    {% for i in range(5) %}
      <fieldset style="margin:10px; border:1px solid #ccc;">
        <legend>Radarr {{i+1}}</legend>
  Enable: <label class="switch"><input name="radarr{{i}}_enabled" type="checkbox" {% if radarr[i].enabled %}checked{% endif %}><span class="slider round"></span></label><br>
        Name: <input name="radarr{{i}}_name" value="{{ radarr[i].name }}"><br>
        URL: <input name="radarr{{i}}_url" value="{{ radarr[i].url }}"><br>
        API Key: <input name="radarr{{i}}_api_key" value="{{ radarr[i].api_key }}"><br>
        Movies to Upgrade: <input name="radarr{{i}}_movies_to_upgrade" value="{{ radarr[i].movies_to_upgrade }}"><br>
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
        <button type="button" onclick="testConnection('sonarr', {{i}})">Test Connection</button>
        <span id="sonarr_status_{{i}}"></span>
      </fieldset>
    {% endfor %}
  </fieldset>
  <br><input type="submit" value="Save Settings">
</form>
<style>
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
  background-color: #2196F3;
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

def load_config():
    with open(CONFIG_PATH, 'r') as f:
        return yaml.safe_load(f)

def save_config(cfg):
    with open(CONFIG_PATH, 'w') as f:
        yaml.safe_dump(cfg, f)


@app.route('/', methods=['GET'])
def index():
  cfg = load_config()
  # Pad radarr/sonarr lists to 5 for UI
  radarr = cfg.get('radarr', [])
  sonarr = cfg.get('sonarr', [])
  while len(radarr) < 5:
    radarr.append({'enabled': False, 'name': f'Radarr {len(radarr)+1}', 'url': '', 'api_key': '', 'movies_to_upgrade': 5})
  while len(sonarr) < 5:
    sonarr.append({'enabled': False, 'name': f'Sonarr {len(sonarr)+1}', 'url': '', 'api_key': '', 'episodes_to_upgrade': 5})
  return render_template_string(SETTINGS_FORM,
    researcharr=cfg.get('researcharr', {}),
    radarr=radarr,
    sonarr=sonarr)


@app.route('/save', methods=['POST'])
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
    })
  cfg['sonarr'] = sonarr
  save_config(cfg)
  flash('Settings saved!')
  return redirect(url_for('index'))


@app.route('/test_connection/<service>/<int:idx>')
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

if __name__ == '__main__':
  app.run(host='0.0.0.0', port=2929, debug=True)
