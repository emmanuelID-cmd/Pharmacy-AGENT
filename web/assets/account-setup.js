/* One-use recovery proof stays in memory; no provider access/refresh tokens. */
(() => {
  'use strict';
  const get = id => document.getElementById(id), form = get('account-setup-form');
  if (!form) return;
  const parameters = new URLSearchParams(window.location.hash.slice(1));
  let proof = parameters.get('token_hash') || '';
  // Remove the secret from this history entry before any user navigation.
  window.history.replaceState(null, '', '/account/setup');
  const fields = ['setup-email', 'setup-password', 'setup-confirm'];
  const valid = id => id === 'setup-email' ? /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(get(id).value.trim()) && get(id).value.trim().length <= 254
    : id === 'setup-password' ? get(id).value.length >= 12 && get(id).value.length <= 1024
    : !!get(id).value && get(id).value === get('setup-password').value;
  let busy = false, used = false;
  function status(text, error = false) {
    const target = get('setup-status'); target.hidden = false; target.textContent = text;
    target.classList.toggle('is-error', error);
  }
  if (!/^[a-f0-9]{40,128}$/.test(proof)) {
    proof = ''; status('Open your complete private setup link. If it expired or was already used, ask Emmanuel for a fresh one.', true);
  }
  fields.forEach(id => get(id).addEventListener('input', () => {
    fields.forEach(field => {
      if (!valid(field)) return;
      get(field).setAttribute('aria-invalid', 'false'); get(field+'-error').hidden = true;
      get('setup-errors').querySelector('a[href="#'+field+'"]')?.closest('li').remove();
    });
    get('setup-errors').hidden = !get('setup-errors').querySelector('li');
  }));
  form.addEventListener('submit', async event => {
    event.preventDefault(); if (busy || form.dataset.configured !== 'true') return;
    if (used) {status('This attempt is finished. Ask Emmanuel for a fresh private setup link.',true);return;}
    const invalid = fields.filter(id => !valid(id)), summary = get('setup-errors');
    summary.replaceChildren(); summary.hidden = !invalid.length;
    fields.forEach(id => {get(id).setAttribute('aria-invalid', String(invalid.includes(id)));get(id+'-error').hidden = !invalid.includes(id);});
    if (invalid.length) {
      const title = document.createElement('strong'); title.textContent = 'Check your account details'; summary.append(title);
      const list = document.createElement('ul');
      invalid.forEach(id => {const item=document.createElement('li'),link=document.createElement('a');link.href='#'+id;link.textContent=get(id+'-error').textContent;link.addEventListener('click',e=>{e.preventDefault();get(id).focus();});item.append(link);list.append(item);});
      summary.append(list);summary.focus();return;
    }
    if (!proof) {status('Ask Emmanuel for a fresh private setup link before submitting.',true);return;}
    busy=true;get('setup-submit').disabled=true;form.setAttribute('aria-busy','true');
    status('Setting your password…');const controller=new AbortController();let timer;
    try {
      const result=await Promise.race([(async()=>{
        const response=await fetch('/api/auth/setup',{method:'POST',headers:{'Content-Type':'application/json'},signal:controller.signal,
          body:JSON.stringify({email:get('setup-email').value.trim(),token_hash:proof,password:get('setup-password').value})});
        const body=await response.json();
        if (!response.ok || body.state!=='PASSWORD_SET') throw Error();
        return body;
      })(),new Promise((_,reject)=>{timer=setTimeout(()=>{controller.abort();reject(Error());},45000);})]);
      form.hidden=true;
      status(result.sessions_revoked ? 'Password set. Return to sign in with your email and new password. Pair your phones again after signing in.'
        : 'Password set. Sign in with your new password. Previous-session cleanup could not be confirmed; ask Emmanuel to check it.');
    } catch (_) {
      status(navigator.onLine===false ? 'No Internet Access. This attempt is unconfirmed. Reconnect and ask Emmanuel for a fresh setup link.'
        : 'Setup was not confirmed. The link may be expired or consumed, or Supabase may have rejected the password. Ask Emmanuel for a fresh link; if you already saw success, try signing in.',true);
    } finally {
      clearTimeout(timer);controller.abort();proof='';used=true;busy=false;
      get('setup-password').value='';get('setup-confirm').value='';get('setup-submit').disabled=false;form.setAttribute('aria-busy','false');
    }
  });
})();
