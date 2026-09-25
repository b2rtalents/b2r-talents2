
document.addEventListener('DOMContentLoaded',()=>{
  document.querySelectorAll('.m-menu-btn').forEach(btn=>{
    btn.addEventListener('click',()=>{
      const nav=btn.closest('.m-header').querySelector('.m-nav');
      const open=nav.classList.toggle('is-open');
      btn.setAttribute('aria-expanded',open?'true':'false');
    });
  });
});
