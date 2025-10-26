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
});
