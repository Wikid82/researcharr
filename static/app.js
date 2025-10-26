document.addEventListener('DOMContentLoaded', ()=>{
  const toggle=document.getElementById('sidebar-toggle');
  const sidebar=document.querySelector('.site-sidebar');
  if(toggle && sidebar){
    toggle.addEventListener('click', ()=>{
      sidebar.classList.toggle('open');
      const expanded = sidebar.classList.contains('open');
      toggle.setAttribute('aria-expanded', expanded);
    });
  }
  // theme toggle
  const themeToggle = document.getElementById('theme-toggle');
  const root = document.documentElement;
  const saved = localStorage.getItem('ra-theme');
  if(saved === 'light') root.classList.add('light');
  if(themeToggle){
    themeToggle.addEventListener('click', ()=>{
      const isLight = root.classList.toggle('light');
      localStorage.setItem('ra-theme', isLight? 'light':'dark');
    });
  }
  // plugin instance actions (validate / sync)
  document.addEventListener('click', function (e) {
    if (e.target.matches('.plugin-validate') || e.target.matches('.plugin-sync')) {
      e.preventDefault();
      const isValidate = e.target.matches('.plugin-validate')
      const plugin = e.target.dataset.plugin
      const idx = e.target.dataset.idx
      const url = `/api/plugins/${encodeURIComponent(plugin)}/${isValidate ? 'validate' : 'sync'}/${idx}`
      const targetSpan = document.getElementById(`result-${plugin}-${idx}`)
      if (targetSpan) targetSpan.textContent = '...working...'
      fetch(url, {method: 'POST', credentials: 'same-origin'})
        .then(r => r.json())
        .then(j => {
          if (targetSpan) {
            if (j.error) targetSpan.textContent = 'Error: ' + (j.msg || j.error)
            else targetSpan.textContent = JSON.stringify(j.result)
          }
        })
        .catch(err => { if (targetSpan) targetSpan.textContent = 'Request failed' })
    }
  })
  // plugin instance modal (add/edit)
  const modal = document.getElementById('plugin-instance-modal')
  const modalTitle = document.getElementById('plugin-instance-modal-title')
  const modalSave = document.getElementById('plugin-instance-modal-save')
  if(modal){
    document.addEventListener('click', function(e){
      const edit = e.target.closest('[data-plugin-edit]')
      const add = e.target.closest('[data-plugin-add]')
      if(edit||add){
        e.preventDefault()
        const plugin = (edit? edit.dataset.pluginEdit : add.dataset.pluginAdd)
        const idx = edit? edit.dataset.idx : null
        modal.dataset.plugin = plugin
        modal.dataset.idx = idx===null? 'new': idx
        modalTitle.textContent = idx===null? `Add instance for ${plugin}` : `Edit instance ${idx} for ${plugin}`
        // clear fields
        modal.querySelector('[name="instance_name"]').value = ''
        modal.querySelector('[name="instance_url"]').value = ''
        modal.querySelector('[name="instance_api_key"]').value = ''
        modal.querySelector('[name="instance_enabled"]').checked = false
        // if editing, attempt to load instance data from DOM dataset (simple approach)
        if(idx!==null){
          // try to fetch instances from server as fallback
          fetch(`/api/plugins` , { credentials: 'same-origin' })
            .then(r=>r.json())
            .then(j=>{
              const p = j.plugins.find(pp=>pp.name===plugin)
              if(p && p.instances && p.instances[idx]){
                const inst = p.instances[idx]
                modal.querySelector('[name="instance_name"]').value = inst.name||''
                modal.querySelector('[name="instance_url"]').value = inst.url||''
                modal.querySelector('[name="instance_api_key"]').value = inst.api_key||''
                modal.querySelector('[name="instance_enabled"]').checked = !!inst.enabled
              }
            }).catch(()=>{})
        }
        modal.classList.add('open')
      }
    })

    // cancel
    modal.querySelector('[data-modal-cancel]').addEventListener('click', ()=>{
      modal.classList.remove('open')
    })

    // save
    modalSave.addEventListener('click', ()=>{
      const plugin = modal.dataset.plugin
      const idx = modal.dataset.idx
      const instance = {
        name: modal.querySelector('[name="instance_name"]').value,
        url: modal.querySelector('[name="instance_url"]').value,
        api_key: modal.querySelector('[name="instance_api_key"]').value,
        enabled: !!modal.querySelector('[name="instance_enabled"]').checked
      }
      // client-side validation
      const errorBox = document.getElementById('plugin-modal-error')
      errorBox.textContent = ''
      if(instance.enabled){
        if(!instance.url || !instance.url.startsWith('http')){
          errorBox.textContent = 'When enabled, URL must start with http/https'
          return
        }
        if(!instance.api_key){
          errorBox.textContent = 'When enabled, API key is required'
          return
        }
      }
      const action = idx==='new' ? 'add':'update'
      fetch(`/api/plugins/${encodeURIComponent(plugin)}/instances`,{
        method:'POST',
        headers:{'Content-Type':'application/json'},
        credentials:'same-origin',
        body: JSON.stringify({action:action, idx: idx==='new'? null: parseInt(idx,10), instance: instance})
      }).then(r=>r.json()).then(j=>{
        if(j.error){
          errorBox.textContent = j.msg || j.error || 'Save failed'
        } else if (j.warning){
          errorBox.textContent = j.warning
        } else {
          location.reload()
        }
      }).catch(()=>{ errorBox.textContent = 'Request failed' })
    })
  }
  // delete handler (confirm + API)
  document.addEventListener('click', function(e){
    const del = e.target.closest('[data-plugin-delete]')
    if(!del) return
    e.preventDefault()
    const plugin = del.dataset.pluginDelete
    const idx = parseInt(del.dataset.idx,10)
    if(!confirm(`Delete instance ${idx} for plugin ${plugin}? This cannot be undone.`)) return
    fetch(`/api/plugins/${encodeURIComponent(plugin)}/instances`,{
      method:'POST', headers:{'Content-Type':'application/json'}, credentials:'same-origin',
      body: JSON.stringify({action:'delete', idx: idx})
    }).then(r=>r.json()).then(j=>{
      if(j.error) alert('Delete failed: '+(j.msg||j.error))
      else location.reload()
    }).catch(()=>{alert('Request failed')})
  })

  // Make all H1 headers collapsible: add a class and toggle the next
  // element's visibility on click. We intentionally do not alter server-
  // side templates; this is a progressive enhancement applied on the
  // client so tests that inspect HTML still see the same content.
  try {
    document.querySelectorAll('h1').forEach(h => {
      h.classList.add('collapsible-header')
      // Toggle the immediately following element (if any)
      const next = h.nextElementSibling
      if (next) {
        next.classList.add('collapsible-content')
        // Start expanded by default; tests expect visible content. If
        // you'd prefer collapsed default, remove the following line.
        // next.classList.remove('collapsed')
      }
      h.addEventListener('click', () => {
        if (next) next.classList.toggle('collapsed')
        h.classList.toggle('open')
      })
    })
  } catch (err) {
    // Fail silently; progressive enhancement only.
  }
});
