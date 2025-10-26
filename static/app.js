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
});
